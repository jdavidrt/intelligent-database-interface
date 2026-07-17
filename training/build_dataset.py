"""Build the LoRA fine-tuning datasets for sql_generator and query_understanding.

Sources:
- databases/soundwave/03_soundwave_edge_cases.md — the 30 hand-verified gold pairs.
- training/soundwave_augmentation.py — authored paraphrases, value substitutions,
  EC-02/EC-04 targeted pairs, probe-wording eval golds, QU intent extras.

Every example replicates the EXACT runtime prompt of its agent:
- sql_generator: SYSTEM_PROMPT + "Schema:/Relevant context:/User intent:/Original
  query:/Entities referenced:/Filters:" blocks (see backend/app/agents/sql_generator.py),
  target in the "### Rationale / ### SQL" format its regex extracts.
- query_understanding: SYSTEM_PROMPT + "Schema context:\\n...\\n\\nUser question: ..."
  (see backend/app/agents/query_understanding.py), target is the Intent JSON.

Anti-contamination: the original wording of every gold (and the 8 gate_d1.py probe
wordings) goes ONLY to the eval split; training sees paraphrases and substitutions.

Every SQL is execution-validated against the same in-memory SQLite the runtime
uses (FileConnector). Hand-verified MySQL that SQLite cannot run is kept but
tagged validated="mysql_only"; failing substituted variants are dropped.

Run from the repo root (requires backend deps — chromadb, sqlglot, sentence-transformers):
    python training/build_dataset.py

Outputs (data/synthetic/):
    sql_generator_train.jsonl / sql_generator_eval.jsonl
    query_understanding_train.jsonl / query_understanding_eval.jsonl
    dataset_stats.json
"""

# ruff: noqa: E402  — imports follow the sys.path bootstrap below
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

import sqlglot
from sqlglot import exp

from backend.app.agents.context_manager import ContextManager
from backend.app.agents.query_understanding import SYSTEM_PROMPT as QU_SYSTEM_PROMPT
from backend.app.agents.sql_generator import (
    SYSTEM_PROMPT as SQLGEN_SYSTEM_PROMPT,
)
from backend.app.agents.sql_generator import (
    _build_schema_summary,
)
from backend.app.services.db.file_connector import FileConnector
from backend.app.services.memory.vector import query_context
from training.soundwave_augmentation import (
    GOLD_META,
    PROBE_EVAL,
    QU_EXTRA,
    TARGETED,
)

DB_NAME = "soundwave"
EDGE_CASES_MD = os.path.join(REPO_ROOT, "databases", DB_NAME, "03_soundwave_edge_cases.md")
OUT_DIR = os.path.join(REPO_ROOT, "data", "synthetic")
N_CONTEXT = 4  # both agents retrieve 4 passages at runtime
MAX_SUB_FORMS = 3  # cap wordings per substitution so easy patterns don't dominate


# ---------------------------------------------------------------------------
# Gold catalog parsing
# ---------------------------------------------------------------------------

_GOLD_BLOCK_RE = re.compile(
    r"### (Q\d{2}) — .*?\n(.*?)\*\*Correct SQL:\*\*\s*```sql\n(.*?)```",
    re.DOTALL,
)
_FIELD_RE = {
    "ec": re.compile(r"\|\s*\*\*EC\*\*\s*\|\s*(.+?)\s*\|"),
    "tier": re.compile(r"\|\s*\*\*Tier\*\*\s*\|\s*(.+?)\s*\|"),
    "nl": re.compile(r"\|\s*\*\*NL\*\*\s*\|\s*\"(.+?)\"\s*\|", re.DOTALL),
}


def parse_gold_catalog(path: str = EDGE_CASES_MD) -> dict[str, dict]:
    """Parse Q01..Q30 out of the edge-case markdown catalog."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    golds: dict[str, dict] = {}
    for match in _GOLD_BLOCK_RE.finditer(text):
        qid, header, sql = match.group(1), match.group(2), match.group(3).strip()
        entry: dict[str, Any] = {"sql": sql}
        for key, rx in _FIELD_RE.items():
            m = rx.search(header)
            entry[key] = m.group(1).strip() if m else ""
        golds[qid] = entry
    if len(golds) != 30:
        raise RuntimeError(f"Expected 30 gold queries in {path}, parsed {len(golds)}.")
    return golds


# ---------------------------------------------------------------------------
# Intent derivation (entities/metrics auto-extracted from the gold SQL)
# ---------------------------------------------------------------------------

_METRIC_PATTERNS = [
    (re.compile(r"\bCOUNT\s*\(\s*DISTINCT\b", re.IGNORECASE), "COUNT DISTINCT"),
    (re.compile(r"\bCOUNT\s*\(", re.IGNORECASE), "COUNT"),
    (re.compile(r"\bSUM\s*\(", re.IGNORECASE), "SUM"),
    (re.compile(r"\bAVG\s*\(", re.IGNORECASE), "AVG"),
    (re.compile(r"\bMIN\s*\(", re.IGNORECASE), "MIN"),
    (re.compile(r"\bMAX\s*\(", re.IGNORECASE), "MAX"),
    (re.compile(r"\bDENSE_RANK\s*\(", re.IGNORECASE), "DENSE_RANK"),
    (re.compile(r"\bRANK\s*\(", re.IGNORECASE), "RANK"),
]


def derive_metrics(sql: str, extra: list[str] | None = None) -> list[str]:
    metrics: list[str] = []
    for rx, label in _METRIC_PATTERNS:
        if rx.search(sql) and label not in metrics:
            # RANK() also matches inside DENSE_RANK() — skip the double count.
            if label == "RANK" and "DENSE_RANK" in metrics:
                if not re.search(r"(?<!DENSE_)RANK\s*\(", sql, re.IGNORECASE):
                    continue
            metrics.append(label)
    for m in extra or []:
        if m not in metrics:
            metrics.append(m)
    return metrics


def derive_entities(sql: str) -> list[str]:
    """Tables + column names referenced by the SQL, in first-appearance order."""
    try:
        tree = sqlglot.parse_one(sql, dialect="mysql")
    except Exception:
        return []
    seen: list[str] = []
    for table in tree.find_all(exp.Table):
        if table.name and table.name not in seen:
            seen.append(table.name)
    for col in tree.find_all(exp.Column):
        if col.name and col.name != "*" and col.name not in seen:
            seen.append(col.name)
    return seen


def build_intent(nl: str, sql: str, meta: dict) -> dict:
    return {
        "entities": derive_entities(sql),
        "metrics": derive_metrics(sql, meta.get("metrics_extra")),
        "filters": list(meta.get("filters", [])),
        "requested_fields": [],
        "time_range": meta.get("time_range"),
        "ambiguity_flags": list(meta.get("ambiguity_flags", [])),
        "plain_restatement": meta["restatement"],
    }


# ---------------------------------------------------------------------------
# Prompt assembly — mirrors the runtime agents exactly
# ---------------------------------------------------------------------------


def sqlgen_user_message(schema_summary: str, context_str: str, intent: dict, nl: str) -> str:
    """Replicates backend/app/agents/sql_generator.py::SQLGenerator.generate()."""
    lines = [
        f"Schema:\n{schema_summary}",
        f"Relevant context:\n{context_str}",
        f"User intent: {intent['plain_restatement']}",
        f"Original query: {nl}",
    ]
    if intent["requested_fields"]:
        lines.append(
            "Explicitly requested output fields (MUST appear in the SELECT list, "
            f"resolved against the schema above): {', '.join(intent['requested_fields'])}"
        )
    if intent["entities"]:
        lines.append(f"Entities referenced: {', '.join(intent['entities'])}")
    if intent["filters"]:
        lines.append(f"Filters: {', '.join(intent['filters'])}")
    return "\n\n".join(lines)


def sqlgen_target(rationale: str, sql: str) -> str:
    return f"### Rationale\n{rationale}\n\n### SQL\n```sql\n{sql}\n```"


def qu_user_message(context_str: str, nl: str) -> str:
    """Replicates backend/app/agents/query_understanding.py::QueryUnderstanding.parse()."""
    return f"Schema context:\n{context_str}\n\nUser question: {nl}"


def qu_target(intent: dict) -> str:
    return json.dumps(intent, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Execution validation
# ---------------------------------------------------------------------------


class Validator:
    def __init__(self, connector: FileConnector) -> None:
        self._db = connector

    def check(self, sql: str) -> tuple[str, int, str]:
        """Returns (status, row_count, error). status: executed | mysql_only | failed."""
        try:
            rows = self._db.execute_read(sql, limit=500)
            return "executed", len(rows), ""
        except Exception as e:
            return "failed", 0, str(e)


# ---------------------------------------------------------------------------
# Substitutions
# ---------------------------------------------------------------------------


def apply_text_map(text: str, mapping: dict[str, str]) -> str:
    # Longest keys first so "Colombian artists" isn't clobbered by "Colombia".
    for src in sorted(mapping, key=len, reverse=True):
        text = text.replace(src, mapping[src])
    return text


def sub_wordings(wordings: list[str], nl_map: dict[str, str]) -> list[str]:
    """Apply an NL substitution to every wording containing one of its tokens."""
    out = []
    for w in wordings:
        if any(tok in w for tok in nl_map):
            out.append(apply_text_map(w, nl_map))
    return out[:MAX_SUB_FORMS]


# ---------------------------------------------------------------------------
# Example assembly
# ---------------------------------------------------------------------------


def make_records(
    *,
    example_id: str,
    ec: str,
    nl: str,
    sql: str,
    meta: dict,
    split: str,
    schema_summary: str,
    validator: Validator,
    note: str = "",
) -> tuple[dict | None, dict | None]:
    """Build the (sql_generator, query_understanding) JSONL records for one pair.

    Returns (None, None) when the SQL fails execution and isn't hand-verified gold.
    """
    status, rows, error = validator.check(sql)
    hand_verified = meta.get("hand_verified", True)
    if status == "failed":
        if not hand_verified:
            print(f"  [drop] {example_id}: {error}")
            return None, None
        status = "mysql_only"
        print(f"  [mysql_only] {example_id}: {error}")

    min_rows = meta.get("min_rows", 1)
    if status == "executed" and rows < min_rows:
        if not hand_verified:
            print(f"  [drop] {example_id}: returned {rows} rows (< {min_rows})")
            return None, None
        print(f"  [warn] {example_id}: returned {rows} rows (< {min_rows})")

    intent = build_intent(nl, sql, meta)
    context_str = "\n".join(query_context(nl, n_results=N_CONTEXT))

    common_meta = {
        "id": example_id,
        "ec": ec,
        "split": split,
        "validated": status,
        "result_rows": rows,
    }
    if note:
        common_meta["note"] = note

    sqlgen_record = {
        "messages": [
            {"role": "system", "content": SQLGEN_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": sqlgen_user_message(schema_summary, context_str, intent, nl),
            },
            {"role": "assistant", "content": sqlgen_target(meta["rationale"], sql)},
        ],
        "meta": {**common_meta, "nl": nl, "gold_sql": sql},
    }
    qu_record = {
        "messages": [
            {"role": "system", "content": QU_SYSTEM_PROMPT},
            {"role": "user", "content": qu_user_message(context_str, nl)},
            {"role": "assistant", "content": qu_target(intent)},
        ],
        "meta": {**common_meta, "nl": nl},
    }
    return sqlgen_record, qu_record


def normalize_nl(nl: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", nl.lower()).strip()


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------
# The external gretelai/synthetic_text_to_sql mix lives in training/gretel_mix.py
# (dependency-light so the Colab notebook can import it without the backend stack).


def build() -> dict:
    print(f"[build_dataset] loading {DB_NAME} profile + embeddings (offline)...")
    connector = FileConnector(DB_NAME)
    connector.connect()
    profile = ContextManager(connector).build_profile()
    schema_summary = _build_schema_summary(profile)
    validator = Validator(connector)
    golds = parse_gold_catalog()

    sqlgen: dict[str, list[dict]] = {"train": [], "eval": []}
    qu: dict[str, list[dict]] = {"train": [], "eval": []}

    def add(split: str, sg: dict | None, q: dict | None) -> None:
        if sg is not None:
            sqlgen[split].append(sg)
            qu[split].append(q)

    # ---- 1. Gold catalog: originals + held-out paraphrase -> eval; rest -> train
    print("[build_dataset] gold catalog Q01..Q30...")
    for qid, gold in golds.items():
        meta = GOLD_META[qid]
        sql, ec = gold["sql"], gold["ec"]

        add(
            "eval",
            *make_records(
                example_id=f"{qid}-orig",
                ec=ec,
                nl=gold["nl"],
                sql=sql,
                meta=meta,
                split="eval",
                schema_summary=schema_summary,
                validator=validator,
            ),
        )
        add(
            "eval",
            *make_records(
                example_id=f"{qid}-p0",
                ec=ec,
                nl=meta["paraphrases"][0],
                sql=sql,
                meta=meta,
                split="eval",
                schema_summary=schema_summary,
                validator=validator,
            ),
        )
        for i, wording in enumerate(meta["paraphrases"][1:], start=1):
            add(
                "train",
                *make_records(
                    example_id=f"{qid}-p{i}",
                    ec=ec,
                    nl=wording,
                    sql=sql,
                    meta=meta,
                    split="train",
                    schema_summary=schema_summary,
                    validator=validator,
                ),
            )

        # Value substitutions -> train (semantics inherited from the verified pattern,
        # but each variant must still execute).
        all_wordings = [gold["nl"]] + meta["paraphrases"]
        for s_idx, sub in enumerate(meta.get("subs", [])):
            sub_sql = apply_text_map(sql, sub["sql"])
            sub_meta = {
                **meta,
                "hand_verified": False,
                "min_rows": 0,
                "restatement": apply_text_map(meta["restatement"], {**sub["nl"], **sub["sql"]}),
                "filters": [
                    apply_text_map(f, {**sub["nl"], **sub["sql"]}) for f in meta.get("filters", [])
                ],
                "time_range": (
                    apply_text_map(meta["time_range"], sub["nl"])
                    if meta.get("time_range")
                    else None
                ),
            }
            for w_idx, wording in enumerate(sub_wordings(all_wordings, sub["nl"])):
                add(
                    "train",
                    *make_records(
                        example_id=f"{qid}-s{s_idx}w{w_idx}",
                        ec=ec,
                        nl=wording,
                        sql=sub_sql,
                        meta=sub_meta,
                        split="train",
                        schema_summary=schema_summary,
                        validator=validator,
                    ),
                )

    # ---- 2. Targeted EC-02 / EC-04 pairs: paraphrase[0] -> eval, rest -> train
    print("[build_dataset] targeted EC-02/EC-04 pairs...")
    for pair in TARGETED:
        add(
            "eval",
            *make_records(
                example_id=f"{pair['id']}-p0",
                ec=pair["ec"],
                nl=pair["paraphrases"][0],
                sql=pair["sql"],
                meta=pair,
                split="eval",
                schema_summary=schema_summary,
                validator=validator,
            ),
        )
        for i, wording in enumerate([pair["nl"]] + pair["paraphrases"][1:]):
            add(
                "train",
                *make_records(
                    example_id=f"{pair['id']}-w{i}",
                    ec=pair["ec"],
                    nl=wording,
                    sql=pair["sql"],
                    meta=pair,
                    split="train",
                    schema_summary=schema_summary,
                    validator=validator,
                ),
            )

    # ---- 3. Probe wordings -> eval only (the execution-accuracy benchmark set)
    print("[build_dataset] gate_d1 probe wordings (eval only)...")
    for probe in PROBE_EVAL:
        add(
            "eval",
            *make_records(
                example_id=probe["id"],
                ec=probe["ec"],
                nl=probe["nl"],
                sql=probe["sql"],
                meta=probe,
                split="eval",
                schema_summary=schema_summary,
                validator=validator,
                note=probe.get("note", ""),
            ),
        )

    # ---- 4. QU-only extras (requested_fields + ambiguity discipline)
    print("[build_dataset] query_understanding intent extras...")
    for i, extra in enumerate(QU_EXTRA):
        context_str = "\n".join(query_context(extra["nl"], n_results=N_CONTEXT))
        qu[extra["split"]].append(
            {
                "messages": [
                    {"role": "system", "content": QU_SYSTEM_PROMPT},
                    {"role": "user", "content": qu_user_message(context_str, extra["nl"])},
                    {"role": "assistant", "content": qu_target(extra["intent"])},
                ],
                "meta": {
                    "id": f"QU-extra-{i:02d}",
                    "ec": "intent",
                    "split": extra["split"],
                    "validated": "n/a",
                    "nl": extra["nl"],
                },
            }
        )

    # ---- 5. Contamination guard + dedup
    for dataset in (sqlgen, qu):
        eval_nls = {normalize_nl(r["meta"]["nl"]) for r in dataset["eval"]}
        dataset["train"] = [
            r for r in dataset["train"] if normalize_nl(r["meta"]["nl"]) not in eval_nls
        ]
        for split in ("train", "eval"):
            seen: set[str] = set()
            unique = []
            for r in dataset[split]:
                key = normalize_nl(r["meta"]["nl"])
                if key in seen:
                    continue
                seen.add(key)
                unique.append(r)
            dataset[split] = unique

    # ---- 6. Write
    os.makedirs(OUT_DIR, exist_ok=True)
    stats: dict[str, Any] = {"db": DB_NAME, "files": {}}
    for name, dataset in (("sql_generator", sqlgen), ("query_understanding", qu)):
        for split, records in dataset.items():
            path = os.path.join(OUT_DIR, f"{name}_{split}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            validated = sum(1 for r in records if r["meta"]["validated"] == "executed")
            stats["files"][f"{name}_{split}"] = {
                "examples": len(records),
                "execution_validated": validated,
                "mysql_only": sum(1 for r in records if r["meta"]["validated"] == "mysql_only"),
            }
            print(f"  wrote {path} — {len(records)} examples ({validated} execution-validated)")

    stats_path = os.path.join(OUT_DIR, "dataset_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"[build_dataset] stats -> {stats_path}")
    connector.disconnect()
    return stats


if __name__ == "__main__":
    build()
