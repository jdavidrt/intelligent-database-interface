"""Transcribe soundwave_30 from databases/soundwave/03_soundwave_edge_cases.sql.

EVALUATION_PROTOCOL.md §2.1 calls soundwave_30 "a census, not a sample:
Q01-Q30 transcribed from the existing 03_soundwave_edge_cases.sql, preserving
each query's `NL:` line as the prompt and its SQL body as the reference.
Difficulty tier and EC tags carry over unchanged."

This is that transcription, done by parser rather than by hand so the manifest
provably matches the source file. Re-running it regenerates the manifest; if the
edge-case file is ever edited, run this again rather than editing the JSONL.

Usage:  python -m evaluation.transcribe_soundwave
"""

from __future__ import annotations

import os
import re

from evaluation.corpus import REPO_ROOT, CorpusItem, write_corpus

SOURCE = os.path.join(REPO_ROOT, "databases", "soundwave", "03_soundwave_edge_cases.sql")

HEADER = re.compile(r"^--\s*\[Q(\d+)\]\s+(.*?)\s+Difficulty:\s*(.+?)\s*$")
NL_START = re.compile(r'^--\s*NL:\s*"(.*)$')
COMMENT = re.compile(r"^--\s?(.*)$")

# §2.2: "set true only when the NL text itself implies an ordering". Only two of
# the thirty do. Q18 says "Rank each artist" but the rank is a column value and
# its reference SQL has no ORDER BY, so row order is not part of the answer;
# Q29 asks for a single row. Neither qualifies.
ORDER_MATTERS = {"Q30"}


def _clean_difficulty(raw: str) -> str:
    """'Extra Hard  (Compositional maximum)' -> 'Extra Hard'."""
    return re.sub(r"\s*\(.*\)\s*$", "", raw).strip()


def parse_blocks(text: str) -> list[dict]:
    lines = text.splitlines()
    blocks: list[dict] = []
    current: dict | None = None
    nl_open = False

    for line in lines:
        header = HEADER.match(line)
        if header:
            if current:
                blocks.append(current)
            number, tags, difficulty = header.groups()
            current = {
                "q": f"Q{int(number):02d}",
                "tags_raw": tags.strip(),
                "difficulty": _clean_difficulty(difficulty),
                "nl_parts": [],
                "sql_lines": [],
            }
            nl_open = False
            continue

        if current is None:
            continue

        nl_start = NL_START.match(line)
        if nl_start:
            body = nl_start.group(1)
            if body.rstrip().endswith('"'):
                current["nl_parts"].append(body.rstrip()[:-1])
            else:
                current["nl_parts"].append(body)
                nl_open = True
            continue

        if nl_open:
            # NL text wrapped onto a continuation comment line.
            comment = COMMENT.match(line)
            if comment:
                body = comment.group(1).strip()
                if body.endswith('"'):
                    current["nl_parts"].append(body[:-1])
                    nl_open = False
                else:
                    current["nl_parts"].append(body)
                continue
            nl_open = False

        if line.startswith("--") or not line.strip():
            continue
        current["sql_lines"].append(line)

    if current:
        blocks.append(current)
    return blocks


def build_items(blocks: list[dict]) -> list[CorpusItem]:
    items: list[CorpusItem] = []
    for block in blocks:
        sql = "\n".join(block["sql_lines"]).strip()
        # Each block's SQL body ends at its terminating semicolon; anything after
        # belongs to the next block's preamble.
        if ";" in sql:
            sql = sql[: sql.index(";")].strip()

        ec_tags = re.findall(r"EC-\d+", block["tags_raw"])
        extra = [
            token.strip()
            for token in block["tags_raw"].split("+")
            if token.strip() and not re.fullmatch(r"EC-\d+", token.strip())
        ]

        items.append(
            CorpusItem(
                id=f"SW-{block['q']}",
                corpus="soundwave_30",
                category=ec_tags[0] if ec_tags else "EC-00",
                difficulty=block["difficulty"],
                nl=" ".join(part.strip() for part in block["nl_parts"]).strip(),
                reference_sql=sql,
                order_matters=block["q"] in ORDER_MATTERS,
                expected_behaviour="answer",
                ec_tags=ec_tags,
                evidence=None,
                accepted_alternatives=[],
                notes=(
                    f"Transcribed verbatim from 03_soundwave_edge_cases.sql [{block['q']}]."
                    + (f" Additional pattern: {', '.join(extra)}." if extra else "")
                ),
            )
        )
    return items


def main() -> None:
    with open(SOURCE, encoding="utf-8") as fh:
        blocks = parse_blocks(fh.read())
    items = build_items(blocks)
    write_corpus("soundwave_30", items)
    print(f"wrote {len(items)} items to data/benchmarks/corpora/soundwave_30.jsonl")
    for item in items:
        print(f"  {item.id}  {item.difficulty:11s} {item.ec_tags}  {item.nl[:58]}")


if __name__ == "__main__":
    main()
