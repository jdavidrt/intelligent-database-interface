# Fine-Tuning Round 1 — Benchmark Diagnosis & Fixes

**Date:** 2026-07-14
**Scope:** First accuracy-improvement pass over the EC-01…EC-08 NL2SQL benchmark (`tests/evaluate.py`), driven by Claude (Fable 5). All changes are prompt/grounding/pipeline engineering — no model weights were trained. This document is the record of what was found, what was fixed, and what remains as genuine LoRA training targets.

**Result:** execution accuracy went from **3/7 to a stable 5–6/7** scored probes (on a *stricter* scoring scale than the baseline used), and one whole query class (date-filtered) became executable for the first time.

---

## 1. Benchmark score progression

All scores below are re-stated on the final (strict) checkers so runs are comparable.

| Run | Score (strict) | What changed before the run |
|---|---|---|
| Baseline (morning run) | 3/7 | — |
| Round 1 fixes | 4/7 | Survey data, profile hardening, meta-filter routing, date UDFs |
| Round 2 fixes | 6/7 | `has_hifi` anchoring, self-join direction rule, regeneration loop |
| Final verification run | 5/7 | Strictest EC-04 checker; EC-02/EC-04 flip on LLM variance |

Run-to-run variance with the 3B model at temperature 0.2 is roughly ±1 probe. The honest steady-state is **5–6/7**, with the failures concentrated in two specific cases (§5).

Per-probe stability across the four post-fix runs:

| EC | Before | After | Notes |
|---|---|---|---|
| EC-01 | 0% | **4/4** | Always generates `country = 'CO'` now |
| EC-02 | flaky | ~30–50% | Model persistently invents genre joins for "high-fidelity" |
| EC-03 | pass | **4/4** | `album_id IS NULL` — never regressed |
| EC-04 | 0% (misrouted) | routing 4/4, correct SQL ~50% | Self-join always generated; side/filter precision varies |
| EC-05 | flaky | **4/4** | `AVG(trk_dur_ms / 60000.0)` |
| EC-06 | false pass | **4/4 strict** | Now correctly emits `effective_to IS NULL` |
| EC-07 | 100% blocked | executes (unscored) | Date-relative vs frozen dataset — unscoreable by design |
| EC-08 | false pass | ~75% genuine | Correct 5-table junction chain most runs |

---

## 2. Harness bugs found (the benchmark itself was broken)

These invalidate naive comparison with any pre-2026-07-14 benchmark numbers:

1. **No database selection.** `gate_d1.py`, `evaluate.py`, and `ab_harness.py` all predate the 2026-07-03 multi-DB restructure and never called `POST /db/select` — they only worked if someone had already picked a database in the frontend, and otherwise every probe silently errored. All three now call a shared `select_db()` helper (`tests/gate_d1.py`).
2. **No diagnostics.** `evaluate.py` didn't record the generated SQL, so failures couldn't be attributed to a pipeline stage. Each per-probe report entry now includes the SQL, row count, clarification/error routing, and the reports in `data/benchmarks/` are actually actionable.
3. **Lenient checkers producing false passes:**
   - EC-06 accepted any result containing 9.99 — a full-price-history scan (the exact EC-06 trap) passed. Now requires exactly 1 row.
   - EC-08 expects 0 rows (no "Adele" in the data), but a verification-*blocked* query also reports 0 rows — indistinguishable from a correct answer. Now requires `verify.overall_passed`.
   - EC-04 accepted any superset containing the 6 parent-genre names. Now requires exactly 6 rows.

---

## 3. Root causes diagnosed

Each was confirmed systematic by re-running the failing probe twice with full verification diagnostics.

### 3.1 Poisoned grounding data (worst finding)
`databases/soundwave/04_soundwave_survey.json` — the human-supplied domain knowledge injected into every DBProfile — was **factually wrong**:
- `plan_type` map swapped Student and Individual (ground truth per seed data: 1=Free, 2=Student, 3=Individual, 4=Family).
- `usr_acq_src` map was wrong on 3 of 4 codes (ground truth per schema comments: 1=organic, 2=social, 3=referral, 4=ad).
- The ISO-3166 country-code convention (documented only in `02_soundwave_context.md`) was absent from everything the SQL generator sees — making EC-01 (`WHERE country = 'Colombia'` → 0 rows) unfixable by the model.

### 3.2 Meta-question filter misrouting (EC-04, 100% failure)
"Which genres have subgenres?" contains no `_SQL_SIGNAL_RE` keyword, isn't caught by any meta/off-topic regex, and is DB-vocabulary-related — so it fell to the LLM fallback classifier in `MetaQuestionFilter.is_meta_question`, which misclassified it as a system-description question. SQL generation never ran; the pipeline answered with DB facts instead of data.

### 3.3 Dialect mismatch hard-blocking all date queries (EC-07, 100% blocked)
The SQL generator emits MySQL (by design), and `FileConnector` transpiles via sqlglot — but sqlglot 30.x leaves `YEAR()`, `MONTH()`, `DAY()`, `NOW()` untranspiled for SQLite. Every date-filtered query failed `EXPLAIN QUERY PLAN` and was correctly blocked by the syntax-verification layer. The fail-safe worked; the query class was simply unreachable.

### 3.4 One bad generation was fatal (EC-02/EC-08 flakiness)
The orchestrator's only recovery on verification failure was a mechanical `= NULL → IS NULL` string repair. There was **no LLM regeneration**, and the syntax layer reported a generic "Engine EXPLAIN rejected the query" with the engine's actual error (e.g. `no such column: t.artist_id`) discarded.

---

## 4. Fixes applied

| # | Fix | Files |
|---|---|---|
| 1 | Corrected both coded-value maps; added country ISO-code, `has_hifi`, `has_downloads` glossary entries; added status/event_type maps | `databases/soundwave/04_soundwave_survey.json` |
| 2 | Country-code rule with the in-data code list (EC-01); explicit nonexistent-FK warnings — `tracks.artist_id`, `play_events.artist_id`, `tracks.genre_id` (EC-08); parent-vs-child self-join direction rule (EC-04) | `backend/app/prompts/sql_generator.md` |
| 3 | `_SQL_SIGNAL_RE` now matches data-shaped interrogatives ("which X have/contain/include Y") with a negative lookahead protecting DB-identity nouns ("which database…") for `_META_RE`; +2 regression tests | `backend/app/agents/clarification.py`, `tests/test_meta_question_filter.py` |
| 4 | Registered SQLite UDFs for `YEAR`/`MONTH`/`DAY`/`NOW` at connection time; `explain()` records `last_explain_error` | `backend/app/services/db/file_connector.py` |
| 5 | Syntax `LayerResult` now carries the engine's real error text | `backend/app/agents/verification.py` |
| 6 | **Regenerate-once-on-verify-fail**: the orchestrator feeds the rejected SQL + the specific failure reason back to the SQL generator and re-verifies. Observed live turning `no such column: sp.subscription_id` into a verified passing query | `backend/app/services/orchestrator.py`, `backend/app/agents/sql_generator.py` |
| 7 | Harness repairs and strict checkers per §2 | `tests/gate_d1.py`, `tests/evaluate.py`, `tests/ab_harness.py` |

Offline test suite: 54 passed (52 pre-existing + 2 new regression tests).

---

## 5. Remaining failures → the actual LoRA training targets

Prompt engineering has plateaued against the 3B base model (qwen2.5-coder-3b-instruct-q4_k_m) on two cases. These are the highest-value training examples for the deferred LoRA fine-tuning phase:

1. **EC-02 — business-term → boolean-flag anchoring.** "High-fidelity audio" must resolve to `subscription_plans.has_hifi = 1`. Despite the glossary entry stating it explicitly, the model invents a genre named 'High-Fidelity' and joins through `track_genres` in ~50–70% of attempts. Training pairs mapping informal product vocabulary onto flag columns should be a core part of the SQL-generator adapter's dataset.
2. **EC-04 — self-join precision.** Routing and structure are now always right, but the model picks the wrong side of the parent/child self-join or appends a spurious filter (`WHERE p.parent_genre_id IS NOT NULL`) in ~50% of attempts. Direction-controlled self-join pairs (have-children vs. are-children-of) belong in the dataset.

Secondary observations for the training phase:
- The regeneration loop rescues hallucinated-column failures but not semantic misdirection — the model repeats its misunderstanding with different syntax.
- The sanity layer has a latent false-positive: any aggregate on the WHERE line is flagged, which will wrongly reject legitimate correlated subqueries (`WHERE x > (SELECT AVG(…))`, edge-case Q15). Worth fixing before Tier-2 probes are added.
- Latency on the GTX 1650: `query_understanding` ~15–18 s, `sql_generator` ~35–40 s per query, tokens/sec 2.3–28 depending on GPU contention. A specialized (smaller-context) profile measurably speeds up generation — visible in EC-02's consistently high tokens/sec.

---

## 6. Operational notes

- **uvicorn `--reload` is unreliable on this Windows setup.** It detected only the first backend file change and never completed the restart, while the stale process kept serving HTTP 200s. An entire benchmark round ran against old code before this was caught. After editing backend `.py` files, restart `start.py` and verify behavior through the event stream, not just endpoint health.
- Instruction profiles (`backend/app/prompts/*.md`) and the survey JSON need **no** restart — profiles are re-read on every adapter activation, the survey on every `POST /db/select`.
- `data/benchmarks/eval_2026-07-14.{json,md}` holds the final instrumented run; the A/B harness (`tests/ab_harness.py`) is fixed and ready for a base-vs-specialized profile comparison when needed.
