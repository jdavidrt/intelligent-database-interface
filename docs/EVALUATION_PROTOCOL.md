# IDI — Evaluation Protocol (Chapter 4 §4.1)

**Version:** 1.2
**Frozen:** 2026-07-21
**Status:** FROZEN — see §0.2 before changing anything in this file.
**Corpora:** authored and frozen — 225 items across four manifests, all conformant
(`python -m evaluation.validate`). No scored run has been executed, so every v1.2 amendment
below is an instrument fix, not a moved target.

This document discharges the blocking pendiente of `IDI_Cuarto_Informe_PENDIENTES.txt` item 1
(Chapter 4 §4.1). It fixes, *before any benchmark is executed*, every degree of freedom that
could otherwise be tuned post-hoc to flatter the results: the frozen clock, the exact
Execution Accuracy comparison algorithm, the Error Detection Rate definition, the latency
measurement conditions, the corpus construction criteria, the heuristic walkthrough script,
and the didactic-clarity checklist and sampling rule.

Chapter 1 §1.13 (recommendation OE4) requires this freeze. Chapter 4 §4.1 should cite this
document; a ready-to-paste Spanish summary is provided in §10.

---

## 0. Freeze discipline

### 0.1 What "frozen" means

No threshold, tolerance, sampling rule, or scoring criterion in this document may be changed
after the first scored benchmark run. Corpus *content* may still be corrected for factual
errors (a reference SQL that is simply wrong), but every such correction must be recorded in
§11 with a justification, and every affected metric must be re-run in full.

### 0.2 Permitted changes

| Change | Allowed after first run? |
|---|---|
| Fix a demonstrably wrong reference SQL | Yes — log in §11, re-run affected corpus |
| Add a query to a corpus | No — corpus sizes are fixed in §2 |
| Change a threshold or tolerance | No |
| Change the EX comparison algorithm | No |
| Add an entry to `accepted_alternatives` (§3.5) | No — these are authored with the corpus, before any run |
| Fix a harness bug that mis-scores a correct answer | Yes — log in §11, re-run affected corpus |

The distinction that matters: **fixing the instrument is allowed; moving the target is not.**

---

## 1. Execution environment

### 1.1 Frozen clock

All runs set:

```
IDI_FREEZE_NOW=2026-07-17T12:00:00
```

The original seed data ended 2025-01-20, which left **every** relative-time window empty at
this instant — "last month", "this year" and "trailing 12 months" all returned zero rows,
which would have silently voided the entire Temporal/Trends category. The data was therefore
extended forward to the freeze instant by
`databases/soundwave/scripts/extend_seed_data.py` (deterministic, `seed=20260721`,
idempotent — re-running regenerates rather than duplicates).

Post-extension the database holds 1,230 `play_events` spanning 2023-01-05 →
2026-07-17 12:00:00, with 40 users, 48 tracks and 20 albums:

| Expression | Resolves to | Seeded events |
|---|---|---|
| "last month" | June 2026 | 78 |
| "this year" | 2026-01-01 … now | 502 |
| "trailing 12 months" | 2025-07-17 … now | 808 |
| "last year" | calendar 2025 | 588 |

Monthly volume ramps gently across the extension (Feb 2026: 68 → Jun 2026: 78), so
"are we growing?" has a defensible answer rather than noise. No row is timestamped after the
freeze instant, so "today" and "this month" cannot pick up future data.

`backend/app/services/clock.py` routes both the agents and the executed SQL
(`file_connector.py` rewrites `CURDATE()`/`NOW()`) through this single frozen instant, so a
date-relative query is fully reproducible. Any run executed without `IDI_FREEZE_NOW` set is
**void** and may not be reported.

**Traps preserved by the extension** — verified by query after generation, not assumed:

| Trap | Post-extension state |
|---|---|
| EC-03 nullable FK | 8 standalone singles (was 5) |
| EC-04 self-reference | referral chain extended by 8 referred users |
| EC-06 temporal SCD | a real 2025-09-01 price change **closes** the previously open `pricing_history` rows and opens new ones; plan 3 now has 4 history rows and a current price of 11.99 |
| EC-07 pre-aggregated vs raw | 378 raw 2026 play events vs 135,166,284 `daily_artist_metrics` streams; cached counters bumped to keep drifting |
| EC-17 value matching | 22 failed/refunded (14 + 8) of **442** payments |

Re-derived ground truth for the hand-written checkers in `tests/evaluate.py` is logged in §11.

### 1.2 Database

- Engine under evaluation: as connected at run time (`FileConnector` in-memory SQLite for
  DB-less runs; MySQL 8.0+ once Day 4 lands). **The engine must be recorded in the run
  header** — EX is not comparable across engines without noting it.
- Schema: `databases/soundwave/01_soundwave_schema.sql` (19 tables).
- Data: `databases/soundwave/02_soundwave_data.sql`, unmodified.
- The database is reset to seed state before each corpus run.

### 1.3 Model and sampling

- Base model: `qwen2.5-coder-3b-instruct-q4_k_m.gguf` via `llama-server`.
- **Decoding: greedy** (`temperature=0`, `top_p=1`, fixed seed). Non-greedy sampling makes EX
  a random variable and is not permitted for scored runs.
- If any scored run is executed with non-greedy sampling, it must be reported as such and
  accompanied by n≥3 repetitions with mean and spread.

### 1.4 Hardware profiles

| Profile | Definition |
|---|---|
| GPU | GTX 1650, 4 GB VRAM, `-ngl 99` |
| CPU-only | same machine, `-ngl 0` |

Both profiles are required by §4.4. All other metrics are reported on the GPU profile.

---

## 2. Corpora

Four corpora, per Chapter 1 §1.3. Sizes are fixed here and may not change.

| ID | Corpus | Size | Manifest | Ch1 threshold |
|---|---|---|---|---|
| `spider_style` | Spider-style simulated subset | 60 | `data/benchmarks/corpora/spider_style.jsonl` | 75% min / 85% target |
| `bird_style` | BIRD-style simulated subset | 60 | `data/benchmarks/corpora/bird_style.jsonl` | 50% min / 60% target |
| `soundwave_30` | SoundWave edge-case suite | 30 | `data/benchmarks/corpora/soundwave_30.jsonl` | diagnostic, no threshold |
| `idi_exec_75` | IDI-EXEC-75 executive language | 75 | `data/benchmarks/corpora/idi_exec_75.jsonl` | 80% min / 90% target |

### 2.1 Construction criterion — and why there is no random seed for the subsets

Chapter 4 §4.1 asks for a "random seed and sampling criterion" for the Spider-style and
BIRD-style subsets. That request presupposes sampling from a pool. It does not apply here,
and saying so explicitly is more honest than inventing a random process after the fact:

**The simulated subsets are authored by stratified construction, not sampled.** There is no
population of SoundWave queries to draw from — the subsets *are* the population. What must
therefore be frozen is not a seed but the **stratification**, fixed below. A seed is fixed
only where genuine sampling occurs: the didactic-clarity review (§8.3).

**Difficulty tiers are computed, not asserted.** Spider defines hardness mechanically in its
own `evaluation.py::eval_hardness`, by counting:

- *component1* — `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`, `JOIN`, `OR`, `LIKE`, `HAVING`
- *component2* — `EXCEPT`, `UNION`, `INTERSECT`
- *others* — whether the query has >1 aggregate, >1 select column, >1 WHERE condition, >1
  GROUP BY column

and binning the counts into easy / medium / hard / extra. The harness reimplements this
function and **labels each item by running it over the reference SQL**, so the tier of an item
is a property of its SQL rather than the author's opinion. An item whose computed tier differs
from its intended tier is re-authored, not relabelled.

**`spider_style` (60 items)** — clean, formal phrasing; no business jargon, no ambiguity. This
subset isolates *structural* difficulty.

| Tier | Share | Count |
|---|---|---|
| easy | 40% | 24 |
| medium | 40% | 24 |
| hard | 15% | 9 |
| extra hard | 5% | 3 |

**`bird_style` (60 items)** — replicates BIRD's dirty-data and external-knowledge pattern:

| Tier | Share | Count |
|---|---|---|
| simple | 50% | 30 |
| moderate | 35% | 21 |
| challenging | 15% | 9 |

> **Disclosure — the mix is deliberately lighter than the official dev sets.** Spider's real
> dev set runs roughly 25/40/22.5/12.5 and BIRD's is harder still. Both distributions here are
> re-weighted toward the easy and medium tiers, because the system under evaluation is a 3B
> quantized model on a 4 GB consumer GPU, not a frontier model with a commercial engineering
> budget. Chapter 1 §1.3 already commits this project to claiming comparability of *difficulty
> class*, never of absolute score, so a lighter mix is methodologically admissible — but only
> if it is stated. §4.2 must report this re-weighting alongside the EX figures. An undisclosed
> re-weighting would be exactly the post-hoc favourable tuning this protocol exists to prevent.

Every item additionally carries an `evidence` field (BIRD's own device: a domain fact not
derivable from the schema, e.g. *"'played' means `event_type = 'play'`, not any row of
play_events"*). At least **40 of the 60** must exercise a dirty-data trap actually embedded in
SoundWave: the `daily_artist_metrics` ETL inflation (EC-07), the cached counters
(`tracks.total_plays`, `artists.monthly_listeners_cached`), nullable FKs, or the
`user_liked_tracks` vs `event_type='save'` overlap. As built, all 60 carry at least one.

> **v1.2 correction.** This paragraph read "at least 20 of the 30" — a leftover from before
> v1.1 raised `bird_style` from 30 items to 60. The two-thirds ratio is preserved. The same
> paragraph described the EC-07 inflation as "~5%"; see §9 quirk 2 for why that figure was
> wrong and what replaced it.

**BIRD tiers are computed too — through a declared mapping.** BIRD's own difficulty labels are
assigned by human annotators, so unlike Spider there is no `eval_hardness` to port. Rather than
let the labels become the author's opinion, `bird_style` derives its tier from the computed
Spider tier through a fixed mapping (`evaluation/hardness.py::BIRD_FROM_SPIDER`): easy and
medium → `simple`, hard → `moderate`, extra → `challenging`. The mapping is part of the freeze.
This is a compromise and worth naming as one: it makes the tier falsifiable and reproducible,
at the cost of measuring structural complexity where BIRD measures something broader.

**`soundwave_30`** — a census, not a sample: Q01–Q30 transcribed from the existing
`databases/soundwave/03_soundwave_edge_cases.sql`, preserving each query's `NL:` line as the
prompt and its SQL body as the reference. Difficulty tier and EC tags carry over unchanged.
The transcription is performed by `evaluation/transcribe_soundwave.py` rather than by hand, so
the manifest provably matches the source file; if the edge-case file is ever edited, that
script is re-run instead of the JSONL being touched. This corpus keeps its own tier vocabulary
(Easy / Medium / Hard / Extra Hard) and is **not** re-scored through `eval_hardness` — §2.1's
"computed, not asserted" rule governs corpora authored for this protocol, whereas these thirty
are inherited evidence whose labels are part of what is being transcribed.

**`idi_exec_75`** — authored to Chapter 1 §1.5's fixed distribution:

| Category | Count |
|---|---|
| Ranking / Top-N | 10 |
| Aggregations / KPIs | 15 |
| Temporal / Trends | 15 |
| Comparisons | 10 |
| Filtering / Segmentation | 10 |
| Relational / Multi-table | 5 |
| Complex Analysis | 5 |
| Deliberate Ambiguity | 5 |

Difficulty split 20% low / 40% medium / 40% high, per Chapter 1 §1.5 — i.e. 15 / 30 / 30.

These levels are computed as well, through `evaluation/hardness.py::EXEC_FROM_SPIDER` (easy →
low, medium → medium, hard and extra → high). The tension is worth stating plainly: Chapter 1
means low/medium/high as *business* difficulty, which is not the same axis as SQL structure —
an executive one-liner can be trivial to ask and hard to answer. Mapping onto the computed
Spider tier trades some fidelity to Ch1's intent for the §2.1 guarantee that no tier is an
unfalsifiable authorial judgement. The five Deliberate Ambiguity items carry no reference SQL
(§2.2) and are counted as `high`.

> **Domain note.** Chapter 1 §1.5 illustrates these categories with sales/retail examples
> ("productos más vendidos", "vendedores", "presupuesto de departamentos"). All four corpora
> execute against SoundWave, so IDI-EXEC-75 is authored in the music-streaming domain. The
> *category definitions and counts* are honoured exactly; only the illustrative examples in
> Ch1 differ from the corpus. This is a documentation mismatch to note when writing §4.2, not
> a change to the metric contract.

### 2.2 Manifest schema

One JSON object per line:

```json
{
  "id": "EXEC-012",
  "corpus": "idi_exec_75",
  "category": "Ranking / Top-N",
  "difficulty": "medium",
  "nl": "which artists are blowing up for us this year?",
  "reference_sql": "SELECT ...",
  "order_matters": true,
  "expected_behaviour": "answer",
  "ec_tags": ["EC-07"],
  "evidence": null,
  "accepted_alternatives": [],
  "notes": ""
}
```

- `expected_behaviour` ∈ `answer` | `clarify` | `block`. See §3.6.
- `order_matters` — set true only when the NL text itself implies an ordering.
- `accepted_alternatives` — see §3.5. Authored with the item, never after a run.
- `reference_sql` is `null` **iff** `expected_behaviour` is `clarify` or `block`. Those two are
  scored on pipeline behaviour, not on a result set (§3.6), so ground truth would be
  meaningless — and a reference query sitting on a `clarify` item invites someone to score it
  by comparison later. `answer` items must carry executable SQL. This constraint was implicit
  in v1.0 and is enforced by `evaluation/corpus.py::check_corpus`.

Conformance of all four manifests against this schema and against §2.1's stratification is
checked offline by `python -m evaluation.validate`, and pinned by `tests/test_corpora.py` so a
corpus cannot drift without a test failing.

---

## 3. Execution Accuracy (EX)

EX = (# items scored `pass`) / (# items in corpus). Reported per corpus, and broken down by
category, difficulty tier, and EC stress pattern (§4.2 requires all three).

### 3.1 Ground truth

Ground truth is the result set produced by executing `reference_sql` against the seeded
database under the frozen clock of §1.1 — *not* a stored literal. This keeps ground truth
correct if the seed data is ever regenerated, and makes the "0 rows" cases (§9) self-evidently
legitimate.

### 3.2 Comparison algorithm

Given candidate result `C` and ground-truth result `G`, both as lists of row-tuples:

1. **Column names are discarded.** Aliases are a free choice of the model and carry no truth
   value. Only positional values are compared.
2. **Column count must match.** `|C[i]| ≠ |G[i]|` → fail. A query that returns the right
   answer plus three extra columns did not answer the question asked. (This is the Spider
   official evaluator's behaviour.)
3. **Row comparison:**
   - `order_matters == false` → compare as **multisets**: sort both row lists by a canonical
     key (tuple of normalized values, NULLs last) and compare element-wise.
   - `order_matters == true` → compare as **ordered lists**, element-wise, no sorting.
   Multiset — not set — comparison is deliberate: it catches a missing or spurious `DISTINCT`.
4. **Row count must match.** Follows from 3.
5. **Value comparison** per §3.3.

### 3.3 Value normalization

| Type | Rule |
|---|---|
| NULL | `NULL == NULL` is **true** for scoring purposes |
| Integer | exact equality |
| Decimal / money | rounded to 2 decimal places, then exact |
| Float / ratio / average | relative tolerance `1e-6`; if `|G| < 1e-9`, absolute tolerance `1e-9` |
| String | compared case-insensitively, whitespace-trimmed (SoundWave collates `utf8mb4_unicode_ci`) |
| Date / datetime | normalized to ISO-8601; a `DATE` equals a `DATETIME` at midnight |
| Boolean / TINYINT(1) | `0`/`1` equal `False`/`True` |

**Units are not normalized.** If ground truth is minutes and the candidate returns
milliseconds, that is a fail unless an `accepted_alternatives` entry says otherwise (§3.5).
Silent unit coercion would hide exactly the semantic error class this project exists to catch.

### 3.4 Non-answers

| Outcome | EX verdict |
|---|---|
| Verification blocked the SQL → nothing executed | **fail** (and counts as an EDR event, §4) |
| Pipeline ended in clarification, `expected_behaviour == "answer"` | **fail** |
| Pipeline error / timeout | **fail** |
| Empty result where ground truth is empty **and** the query actually executed | **pass** |
| Empty result where ground truth is empty but verification blocked the query | **fail** |

The last two rows matter: a blocked query also reports zero rows, and scoring that as a pass
is a false positive. This rule is already implemented correctly in
`tests/evaluate.py::_check_ec08` and generalizes here.

### 3.5 `accepted_alternatives`

Some questions have more than one defensible correct answer — usually a unit or a
representation choice ("average track duration" in minutes or in milliseconds; a count
returned as one row or as one row per group). Where the corpus author judges this to be the
case, the item carries additional reference SQL in `accepted_alternatives`, and the candidate
passes if it matches **any** of them under §3.2–3.3.

These are authored *with the corpus, before any run*, and may not be added afterwards (§0.2).
An alternative added after seeing a failure is threshold tuning wearing a disguise.

### 3.6 `expected_behaviour`

- `answer` — normal scoring per §3.2.
- `clarify` — used by IDI-EXEC-75's five Deliberate Ambiguity items. **Pass** iff the pipeline
  requests clarification instead of guessing; producing SQL is a fail even if that SQL is
  reasonable. These 5 items are scored on this criterion and are included in the IDI-EXEC-75
  EX denominator.
- `block` — the query must be refused (destructive or out-of-scope). Pass iff verification
  blocks it.

---

## 4. Error Detection Rate (EDR)

Chapter 1 §1.8 defines EDR as "the percentage of erroneous SQL queries correctly detected by
the Verification Agent before being executed", threshold 90% / target 95%.

### 4.1 Why the Gate D1 figure is not an EDR

Gate D1's "6 of 8" counts *end-to-end successes*, not *detections of injected errors*. It
cannot be reported as EDR. A purpose-built error corpus is required.

### 4.2 Error-injection corpus

`data/benchmarks/corpora/edr_mutants.jsonl`. Built by applying mutation operators to the
reference SQL of the four corpora. Each mutant is fed **directly to the verification chain**,
bypassing generation, so the metric measures the verifier and not the generator.

| # | Operator | Layer expected to catch it |
|---|---|---|
| M1 | Reference a nonexistent column | semantic |
| M2 | Reference a nonexistent table | semantic |
| M3 | Invent a join key that is not a legal FK edge (e.g. `play_events.artist_id`) | semantic (rule 4b) |
| M4 | `= NULL` instead of `IS NULL` | semantic |
| M5 | Drop a non-aggregated column from GROUP BY | semantic |
| M6 | Put an aggregate in WHERE | sanity |
| M7 | Destructive statement (`DROP`, `DELETE`, `UPDATE`) | sanity (read-only guard) |
| M8 | Multi-statement injection (`SELECT 1; DROP TABLE users`) | sanity |
| M9 | Remove a join predicate, producing a cartesian product | sanity |
| M10 | Invalid enum literal (`event_type = 'listen'`) | semantic |

Target ≥ 10 mutants per operator, ≥ 100 total, drawn across all four corpora so no single
query shape dominates.

### 4.3 Definition

```
EDR = (mutants rejected by the verification chain) / (total mutants)
```

A mutant counts as detected only if it is rejected **before execution**. Rejection for the
wrong reason still counts as detected, but the layer and message are logged so §4.3 of the
report can show *which* layer fired.

### 4.4 Specificity — mandatory companion metric

EDR alone is trivially gamed: a verifier that rejects everything scores 100%. EDR is therefore
**always reported alongside** its false-positive rate on legal SQL, measured over the union of
the four corpora's reference SQL plus the 14-entry legal corpus in
`tests/test_verification_false_positives.py`.

Since 2026-07-21 the verifier emits three verdicts — `pass` / `caution` / `fail` — and a
`caution` **never blocks**: `overall_passed` stays `True` and the query executes, with the
caveat riding into the didactic answer. That distinction is load-bearing here, so specificity
is reported as two separate numbers and never pooled:

```
Hard FPR = (legal queries given verdict `fail`)    / (total legal queries)
Soft FPR = (legal queries given verdict `caution`) / (total legal queries)
```

- **Hard FPR** is the damaging one: a correct query the user never gets to run. Target 0%.
- **Soft FPR** is a *usability* signal, not a correctness failure. A caveat on legal SQL is
  the system being honest about genuine ambiguity — e.g. the deliberately unresolved
  `playlists ↔ tracks` bridge. But a soft FPR near 100% means every answer carries a warning,
  which trains the user to ignore warnings. Report it; do not treat it as a defect on its own.

**An EDR figure published without both FPR figures is not a valid result under this protocol.**
High EDR bought with high hard FPR is a broken verifier, not a good one.

For the mutant corpus, `caution` does **not** count as detection: the mutant still executes,
so the error was not prevented. Only verdict `fail` counts toward EDR.

---

## 5. Latency (§4.4)

- **Query class:** single-table queries, per Chapter 1 §1.8's definition of P50 latency. The
  measurement set is **the first 10 `easy`-tier items of `spider_style` in manifest order**,
  i.e. `SPIDER-001` … `SPIDER-010`, all single-table by construction.

  > **v1.2 correction — this was an open degree of freedom.** v1.0 said "the 10 `easy`-tier
  > items of `spider_style`" while §2.1 gives that tier **24** items. Which ten was never
  > stated, in the one document whose purpose is to close exactly this kind of gap: a latency
  > figure could have been quoted from whichever ten ran fastest. Fixing the rule to the first
  > ten in manifest order costs nothing (they are authored in a fixed order and all are
  > single-table) and removes the choice. `SPIDER-001`…`010` are: list artist names; count
  > tracks; albums by type; root genres; users by join date; users in CO; plans with
  > downloads; explicit tracks; max plan price; distinct artist countries.
- **Repetitions:** 5 per query per profile, 50 samples per profile. First run per profile is
  discarded as warm-up (model load, context build).
- **Measured span:** end to end — user question received → final result available to the
  frontend. Derived from `AgentEvent` timestamps, as `tests/evaluate.py::_stage_latencies`
  already does.
- **Reported statistics:** P50 (the contract metric), plus P90 and max for context.
- **Profiles:** GPU and CPU-only (§1.4). Threshold `< 5s` min / `< 3s` target applies to the
  GPU profile; the CPU-only figure is reported without a threshold.
- **Verification-chain time:** measured separately as the span from `verification` started to
  `verification` done, against the `< 2s` target inherited from Chapter 3 §3.4. Reported as
  P50 over the same 50 samples.
- **Tokens/sec:** read from the `sql_generator` done-event payload
  (`llm_service.chat_with_meta()`), reported as mean and P50.

Latency is measured on otherwise-idle hardware. Any run with another GPU workload resident is
void.

---

## 6. A/B and baseline (§4.5, §4.8)

- **Run A (baseline):** `adapters/registry.json` emptied — all agents on base instructions.
- **Run B:** registry as authored — specialized instruction profiles active.
- Both runs use identical corpora, frozen clock, greedy decoding, and hardware profile.
- The A/B is executed over **all four corpora**, not the 8 EC probes `tests/ab_harness.py`
  currently covers. The harness must be extended before this metric is reported.
- **Mandatory framing:** this A/B measures *instruction profiles*, not trained LoRA adapters.
  Every table reporting it must say so. The LoRA comparison Chapter 1 asked for remains
  pending until training (Chapter 3 §3.10) concludes.
- §4.8 reports every metric in §3–§5 for both runs, so each profile's contribution is
  quantifiable.

---

## 7. Heuristic expert walkthrough (§4.6)

Seven scenarios UC-01–UC-07, scored by the author (optionally the advisor) with no external
participants. This replaces the SUS study discarded in Chapter 1 §1.2.

### 7.1 Checklist — scored per scenario

| # | Criterion | Scale |
|---|---|---|
| C1 | The answer is correct | pass / fail |
| C2 | The answer is intelligible without SQL knowledge | 0–2 |
| C3 | No unexplained technical jargon reaches the user | 0–2 |
| C4 | Clarification questions ≤ 2 | pass / fail |
| C5 | Response time within the scenario's stated budget | pass / fail |
| C6 | The didactic panel adds something the raw answer did not | 0–2 |
| C7 | Failure states, if any, are explained conceptually rather than as stack traces | 0–2 / N-A |

**Critical finding** = C1 fail, or C4 fail, or any 0 on C2/C3. A scenario **passes** iff it
records no critical finding.

**Coverage** = scenarios passed / 7. Threshold ≥ 6/7, target 7/7 (Ch1 §1.8).

### 7.2 Per-scenario execution

Each scenario is run once, from a clean session, with the exact user utterance recorded in the
corpus file `data/benchmarks/corpora/uc_scenarios.jsonl`. Screen output and the `AgentEvent`
stream are both captured.

**UC-06 (silent self-correction)** is scored per Chapter 4's stated rule: success means the
user never sees a wrong result *nor the retry itself*; evidence that self-correction occurred
is sought in the backend `AgentEvent`s and logs, not in the UI.

**UC-03 (multi-turn persistence)** was blocked by KI-1. `tests/test_session_restore.py` now
asserts that assistant turns persist with `sql` and `rows_json` and are returned by
`GET /session/{id}`, so UC-03 is expected to score normally. If it fails in the walkthrough,
it is reported as a critical finding, not deferred.

---

## 8. Didactic clarity (§4.7)

Threshold 75% min / 90% target (Ch1 §1.8).

### 8.1 Unit of analysis

One *explanation*, of which the system produces three kinds:

- **SQL annotation** — the per-clause one-line explanations from the SQL Generator.
- **Domain glossary** — Context Manager term expansions.
- **Chart justification** — the Visualization Engine's one-sentence rationale.

### 8.2 Comprehensibility checklist

An explanation is judged **comprehensible** iff all four hold:

| # | Criterion |
|---|---|
| D1 | Every technical term is either avoided or defined in place |
| D2 | It states *why*, not only *what* — a restatement of the clause in words is not an explanation |
| D3 | It is factually correct with respect to the SQL/chart it describes |
| D4 | A reader with no SQL knowledge could act on it (predict what the clause changes) |

D3 is scored first: a fluent but wrong explanation is worse than none, and is never
comprehensible.

**Metric** = comprehensible explanations / sampled explanations.

### 8.3 Sampling — the one place a seed applies

- **Frame:** all explanations produced during the scored EX runs across the four corpora.
- **Design:** stratified by explanation kind (3 strata) and by corpus (4 strata).
- **Size:** 60 explanations — 20 per kind, allocated across corpora proportionally to corpus
  size: **spider 16 / bird 16 / soundwave 8 / exec 20**, rounded to the stratum.

  > **v1.2 correction.** v1.0 gave this allocation as spider 14 / bird 10 / soundwave 10 /
  > exec 26. Those numbers are proportional to the *pre-v1.1* corpus sizes (40 / 30 / 30 / 75 =
  > 175); the same paragraph in the same document had already raised spider and bird to 60
  > each. Against the actual 60 / 60 / 30 / 75 = 225 the allocation is 16 / 16 / 8 / 20. The
  > stale figures would have over-weighted IDI-EXEC-75 by a third and under-sampled the two
  > largest corpora.
- **Seed:** `20260721` — **provisional**, drawn with `random.Random(20260721)` over the
  explanation list sorted by `(corpus, item_id, kind, ordinal)`. The sorted order makes the
  draw reproducible independently of dict iteration order.

> **Seed policy.** `20260721` is committed now so that pilot runs are reproducible and the
> harness can be developed against a fixed sample. It will be **re-drawn once, immediately
> before the final scored run**, and the new value recorded in §11 with its date. This is the
> one deliberate exception to §0.2, and it is a conservative one: re-drawing the sample for
> the final run prevents the checklist from being unconsciously tuned against the specific 60
> explanations seen during development. The re-draw must happen *before* the final run is
> scored, never after seeing its result — and both the provisional and final figures are
> reported if they differ materially.

### 8.4 Known scope limit

Chapter 3 §3.11 records that chart-choice justification has only a basic implementation
covering general cases. The chart-justification stratum is therefore expected to score lower,
and §4.7 must report the three strata separately rather than only the pooled figure.

---

## 9. Known ground-truth quirks

Recorded here so they are never scored as failures:

1. **EC-08 / "Adele"** — the EC-08 probe asks for playlists containing tracks by Adele. No
   artist named Adele exists in SoundWave's 12-artist catalogue. **The correct answer is 0
   rows**, and only counts as a pass if the query actually executed (§3.4).
2. **EC-07 pre-aggregation** — `daily_artist_metrics.stream_count` sits **290,000× to
   1,070,000×** above `COUNT(play_events)`, measured per artist against the seeded data on
   2026-07-21. **Every EC-07 item must name its source in the question or the `evidence` field,
   and `accepted_alternatives` is forbidden on them** — enforced by
   `evaluation/corpus.py::check_corpus`.

   > **v1.2 correction, and the reason the rule changed.** v1.0 described this gap as "~5%"
   > and prescribed listing both sources in `accepted_alternatives` where a question was
   > answerable from either. The "~5%" figure was the *design intent* recorded throughout the
   > schema comments; it was never what the seed generator produced. The pre-aggregated and
   > cached columns hold production-scale figures while `play_events` is a ~1,000-row teaching
   > sample — The Weeknd shows 225 raw plays against 65,314,971 in `daily_artist_metrics`.
   >
   > At 5% divergence, accepting both sources is a benign tolerance for a representation
   > choice. At 290,000× it is not: an item that accepts both passes on any answer between 225
   > and 65 million, which is no constraint at all. Keeping the v1.0 rule would have produced
   > EX credit for arithmetic nobody checked. The corrected figures have been propagated to
   > `01_soundwave_schema.sql`, `02_soundwave_data.sql`,
   > `00_soundwave_db_documentation.md` §5.4 and `03_soundwave_edge_cases.{sql,md}` Q20.

3. **Cached counters** — `tracks.total_plays` runs **479× to 200,000,000×** above the raw
   event count for the same track, and `artists.monthly_listeners_cached` **2.4M× to 9.1M×**
   above the raw distinct-listener count. Same treatment and same prohibition as quirk 2.
4. **Thin relative-time windows** — see §1.1. Small result sets are correct results.
5. **Empty ground truth in `soundwave_30`** — SW-Q21 ("artists who grew streams >20% from 2023
   to 2024") and SW-Q30 (the compositional-maximum growth query) both return **0 rows** against
   the seeded data. Like the Adele case in quirk 1 these are correct answers and are scored as
   passes under §3.4 — but they discriminate weakly, since a wrong-but-executable query that
   also returns nothing passes too. They are retained because §2.1 requires `soundwave_30` to
   transcribe the syllabus unchanged; they are recorded here so §4.2 does not read their
   passes as evidence of capability. The two authored corpora have no such items: BIRD-036 and
   BIRD-040 were rewritten during authoring when they turned out to have empty ground truth.

---

## 10. Spanish summary for Chapter 4 §4.1

> **4.1. Protocolo de Evaluación.** El protocolo se congeló el 2026-07-21, antes de ejecutar
> cualquier benchmark, y se versiona en `docs/EVALUATION_PROTOCOL.md`. Fija: (i) el reloj
> congelado `IDI_FREEZE_NOW=2026-07-17T12:00:00`, que hace reproducibles las consultas
> relativas al tiempo, junto con la extensión determinista de los datos semilla de SoundWave
> hasta ese mismo instante (1.230 eventos, 2023-01-05 a 2026-07-17, generados por
> `databases/soundwave/scripts/extend_seed_data.py` con semilla 20260721): sin esta extensión
> toda ventana relativa — "el mes pasado", "este año", "los últimos doce meses" — devolvía
> cero filas, lo que habría anulado en silencio la categoría Temporal completa. La extensión
> preserva las trampas EC-02/03/04/06/07/17, verificadas por consulta tras generarlas;
> (ii) decodificación greedy (temperature=0), sin la cual EX sería una variable aleatoria;
> (iii) el criterio exacto de Execution Accuracy — comparación de multiconjuntos de tuplas
> posicionales, sensible al orden solo cuando la pregunta lo implica, con tolerancia relativa
> 1e-6 en flotantes, 2 decimales en valores monetarios, comparación de cadenas insensible a
> mayúsculas (colación `utf8mb4_unicode_ci`), `NULL == NULL`, y sin normalización de unidades;
> (iv) la definición de Error Detection Rate sobre un corpus de mutantes inyectados (10
> operadores, ≥100 mutantes) evaluados directamente contra la cadena de verificación,
> reportado **siempre** junto a su tasa de falsos positivos, pues un verificador que rechaza
> todo obtendría 100% de EDR; (v) las condiciones de medición de latencia (P50 sobre consultas
> de una sola tabla, 5 repeticiones, perfiles GPU y CPU-only, descarte de la corrida de
> calentamiento); (vi) el guion y la checklist del walkthrough heurístico de UC-01–UC-07, con
> su criterio de "hallazgo crítico"; y (vii) la checklist de claridad didáctica y su muestreo
> estratificado de 60 explicaciones con semilla `20260721`.
>
> Sobre la "semilla aleatoria" que este protocolo debía fijar para los subconjuntos simulados:
> no aplica. Los subconjuntos estilo Spider y estilo BIRD no se muestrean de una población
> preexistente — se construyen por autoría estratificada, y por tanto *son* la población. Lo
> que se congela en su lugar es la estratificación: 60 ítems estilo Spider en proporción
> 40/40/15/5 (easy/medium/hard/extra) y 60 estilo BIRD en 50/35/15
> (simple/moderate/challenging). El nivel de dificultad de cada ítem no se declara sino que se
> **calcula**, reimplementando la función `eval_hardness` del evaluador oficial de Spider
> sobre el SQL de referencia, de modo que la etiqueta sea una propiedad de la consulta y no
> una opinión del autor. Esta mezcla es deliberadamente más liviana que la de los dev sets
> oficiales, porque el sistema evaluado es un modelo de 3B cuantizado sobre una GPU de 4 GB;
> el Capítulo 1 §1.3 ya compromete a este trabajo a afirmar comparabilidad de *clase de
> dificultad* y nunca de puntaje absoluto, por lo que la reponderación es admisible — pero se
> declara explícitamente en §4.2, ya que una reponderación no declarada sería precisamente el
> ajuste post-hoc favorable que este protocolo existe para impedir. La semilla se reserva para
> el único muestreo real del capítulo, el de §4.7, y se re-sortea una vez antes de la corrida
> final.
>
> Se deja registrado el ground truth de la prueba EC-08: la artista "Adele" no existe en el
> catálogo de SoundWave, por lo que su respuesta correcta es 0 filas — y solo se puntúa como
> acierto si la consulta efectivamente se ejecutó, dado que una consulta bloqueada por
> verificación también reporta 0 filas.
>
> **Corpus (v1.2).** Los cuatro corpus quedaron redactados y congelados el 2026-07-21: 225
> ítems en total (60 estilo Spider, 60 estilo BIRD, 30 de SoundWave y 75 de IDI-EXEC), de los
> cuales 220 llevan SQL de referencia que **se ejecuta efectivamente** contra la base con reloj
> congelado; los 5 restantes son los ítems de Ambigüedad Deliberada, que por §3.6 se puntúan
> por comportamiento y deliberadamente no llevan consulta de referencia. La conformidad —
> tamaños, esquema del manifiesto, estratificación y ejecutabilidad — se verifica de forma
> automática y sin modelo mediante `python -m evaluation.validate`, y queda fijada por
> `tests/test_corpora.py`. El nivel de dificultad de los tres corpus redactados para este
> protocolo se **calcula** sobre el SQL de referencia: directamente con la reimplementación de
> `eval_hardness` en el caso Spider, y mediante dos mapeos declarados (`BIRD_FROM_SPIDER`,
> `EXEC_FROM_SPIDER`) en los otros dos, lo cual se documenta como un compromiso explícito —
> hace la etiqueta falsable y reproducible, al costo de medir complejidad estructural donde
> BIRD y el Capítulo 1 miden algo más amplio.
>
> **Corrección sustantiva de v1.2.** La divergencia EC-07 entre la tabla pre-agregada y el log
> crudo no es del "~5%" que afirmaban el esquema, este protocolo y la documentación de la base:
> medida contra los datos sembrados es de **290.000× a 1.070.000×** (The Weeknd registra 225
> reproducciones crudas frente a 65.314.971 en `daily_artist_metrics`), porque las columnas
> cacheadas y pre-agregadas se sembraron a escala de producción mientras que `play_events` es
> una muestra didáctica de unas mil filas. La cifra del 5% era la intención de diseño y nunca
> fue lo que generó el sembrador. La magnitud importa metodológicamente: con un 5% es
> defendible aceptar ambas fuentes como correctas, pero con 290.000× un ítem que acepte ambas
> es infalsable —cualquier respuesta entre 225 y 65 millones pasaría—, de modo que la regla
> quedó invertida: todo ítem EC-07 debe **nombrar su fuente** y tiene prohibido el campo
> `accepted_alternatives`. Se corrigieron además tres cifras heredadas de versiones anteriores
> del corpus (el total de pagos, la asignación muestral de §8.3 y el "20 de 30" de §2.1), se
> fijó el subconjunto exacto de diez consultas para la medición de latencia de §5 —que había
> quedado sin especificar sobre un estrato de 24— y se corrigió un SQL de referencia
> demostrablemente erróneo (Q22, cuyo `COUNT(*)` tras un LEFT JOIN contaba eventos y no pistas).

---

## 11. Change log

| Date | Change | Justification | Metrics re-run |
|---|---|---|---|
| 2026-07-21 | v1.0 — initial freeze | — | — |
| 2026-07-21 | v1.1 — clock moved to `2026-07-17T12:00:00`; seed data extended forward | Project decision to align the benchmark clock with the system's operating date. Required extending SoundWave, since the original data ended 2025-01-20 and left every relative-time window empty | none yet run |
| 2026-07-21 | v1.1 — `spider_style` 40→60, `bird_style` 30→60; difficulty re-weighted toward easy/medium; tiers now computed via Spider's `eval_hardness` | Larger corpora give finer EX resolution; lighter mix matches a 3B local model. Disclosed in §2.1 | none yet run |
| 2026-07-21 | v1.1 — FPR split into hard/soft to reflect the `pass`/`caution`/`fail` verdict | A `caution` never blocks, so pooling it with `fail` would overstate the damage | none yet run |
| 2026-07-21 | v1.1 — §8.3 seed marked provisional, to be re-drawn before the final run | Prevents the clarity checklist being tuned against the development sample | none yet run |
| 2026-07-21 | **v1.2 — all four corpora authored and frozen** (225 items). `evaluation/` package added: `hardness.py` (Spider `eval_hardness` port), `corpus.py` (manifest schema + conformance), `validate.py`, `transcribe_soundwave.py`, `authoring/build_*.py` | Discharges §2. Every reference query executes against the frozen-clock DB; every tier is computed, not declared | none yet run |
| 2026-07-21 | v1.2 — §9 quirk 2/3: EC-07 divergence corrected from "~5%" to the measured 290,000×–1,070,000× (and the cached counters to 479×–2×10⁸ and 2.4M×–9.1M×); `accepted_alternatives` now **forbidden** on EC-07 items | The "~5%" was design intent never realised by the seed generator. At the true spread, accepting both sources makes an item unfalsifiable — the v1.0 rule would have granted EX credit unconditionally. Corrected figures propagated to the schema, data, documentation and edge-case files | none yet run |
| 2026-07-21 | v1.2 — §8.3 sampling allocation corrected from 14/10/10/26 to **16/16/8/20** | The v1.0 figures were proportional to the pre-v1.1 corpus sizes (40/30/30/75); against the current 60/60/30/75 they over-weighted IDI-EXEC-75 by a third | none yet run |
| 2026-07-21 | v1.2 — §2.1 "at least 20 of the 30" dirty-data traps corrected to **40 of the 60** | Same staleness: `bird_style` became 60 items in v1.1 and this sentence was not updated. Ratio preserved | none yet run |
| 2026-07-21 | v1.2 — §5 latency measurement set pinned to **`SPIDER-001`…`SPIDER-010`** | v1.0 said "the 10 easy-tier items" while that tier holds 24. An unspecified choice of ten is exactly the post-hoc freedom this document exists to remove | none yet run |
| 2026-07-21 | v1.2 — §1.1 payment total corrected from 421 to **442** | Re-counted against the extended seed. The "22 failed/refunded" figure was correct (14 failed + 8 refunded) | none yet run |
| 2026-07-21 | v1.2 — §2.2: `reference_sql` must be null iff `expected_behaviour` is `clarify`/`block` | Implicit in v1.0's §3.6. Made explicit and enforced so nobody later scores a clarify item by result comparison | none yet run |
| 2026-07-21 | v1.2 — BIRD and IDI-EXEC tiers declared to be **computed** via `BIRD_FROM_SPIDER` / `EXEC_FROM_SPIDER` | §2.1 forbade asserted tiers but only Spider had a mechanical definition. The mappings extend the guarantee to the other two corpora, at a documented cost in fidelity to BIRD's and Ch1's own notions of difficulty | none yet run |
| 2026-07-21 | v1.2 — **corpus correction**: `03_soundwave_edge_cases.sql` Q22 reference SQL fixed (`COUNT(*)` → `COUNT(DISTINCT t.track_id)`) | Demonstrably wrong reference SQL, permitted by §0.2. The LEFT JOIN fans out to one row per play event, so `total_tracks` reported 963 (events) instead of 48 (tracks). The percentage survived only because the numerator is currently 0. Manifest regenerated from the corrected source | none yet run |
| 2026-07-21 | v1.2 — **corpus correction**: BIRD-036 and BIRD-040 re-authored | Both had empty ground truth against the seeded data ("artists with no analytics rows", "tracks never played" — neither exists). An item with an empty answer passes for any executable query returning nothing. Replaced with same-shape, same-tier anti-joins that have real answers. Caught during authoring, before any run | none yet run |
| 2026-07-21 | v1.2 — `tests/evaluate.py`: EC-07 checker added; stale comment removed | The probe was excluded as "date-relative against a dataset frozen at 2025-01-20", a premise the v1.1 seed extension invalidated. "Last month" is now June 2026 and the answer is The Weeknd with 13 plays | none yet run |
| 2026-07-21 | v1.2 — run presets added (`run_benchmarks.py`, `evaluation/plan.py`): 30m/1h/3h/full at 20/41/123/225 items, the 30m one easy-weighted | **Instrument, not target.** No threshold, corpus, tier definition or scoring rule changes. The presets only decide how much of the frozen corpora a *pilot* run executes; every one but `full` is written with `reportable: false`, and the easy-weighted mix is declared in the header caveats because it inflates EX by construction. Selection stays a manifest-order prefix of each stratum, fixed before the first query (§0), and is pinned offline by `tests/test_eval_plan.py` | none yet run |
| 2026-07-21 | v1.2 — `00_soundwave_db_documentation.md` §7 row counts re-derived | The whole table predated the seed extension: play_events listed at ~150 against an actual 1,230, payments at 20 against 442, users at 20 against 40, and coverage as "8 full quarters (Jan 2023 – Jan 2025)" against an actual 2023-01-05 → 2026-07-17 | none yet run |

### 11.1 Ground truth re-derived after the seed extension

`tests/evaluate.py` carries hand-derived expected values. Re-verified 2026-07-21 by query
against the extended database; changed values updated in place:

| Checker | Was | Now | Cause |
|---|---|---|---|
| `_check_ec01` (CO artists) | Karol G | Karol G | unchanged — no CO artists added |
| `_check_ec02` (hi-fi plans) | Individual, Family | Individual, Family | unchanged |
| `_check_ec03` (standalone singles) | 5 | **8** | tracks 46–48 added with `album_id NULL` |
| `_check_ec04` (parent genres) | 6 | 6 | unchanged — no genres added |
| `_check_ec05` (avg duration) | 3.648 min | **3.5852 min** | tracks 31–48 added; still inside the 3.4–3.9 band, band unchanged |
| `_check_ec06` (current price) | 9.99 | **11.99** | 2025-09-01 price change closes the old open SCD row |
| `_check_ec08` (Adele) | 0 rows | 0 rows | unchanged |
| `_check_ec07` (most plays last month) | *not scored* | **The Weeknd, 13 plays** | newly derivable — see §11.2 |

The four benchmark corpora need no equivalent edit: their ground truth is computed by
executing reference SQL (§3.1), so it tracks the data automatically.

### 11.2 EC-07 restored to the scored set

`tests/evaluate.py` excluded the EC-07 probe with the comment *"date-relative against a
dataset frozen at 2025-01-20 — not fixed-derivable, intentionally not scored"*. The v1.1 seed
extension moved the data to the frozen clock and invalidated that premise, but the exclusion
was never revisited, so the probe stayed dark for a reason that had stopped being true.

Under `IDI_FREEZE_NOW=2026-07-17T12:00:00`, "last month" is June 2026 (78 events) and the
answer to *"Which artist had the most plays last month?"* is **The Weeknd with 13 plays**.

The checker cannot test the artist name alone: `daily_artist_metrics` also ranks The Weeknd
first for that window, at 4,966,274 streams. The name is identical under both readings and only
the magnitude distinguishes them, so `_check_ec07` additionally rejects any count above 1000 as
having been answered from the pre-aggregated table. A probe that checked only the name would
have scored the EC-07 trap as passed while the model fell straight into it.
