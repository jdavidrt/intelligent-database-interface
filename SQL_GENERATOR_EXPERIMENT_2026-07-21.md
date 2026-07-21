# SQL Generator — Improvement Experiment, 2026-07-21

**Outcome: reverted.** Five changes were made together, measured against the first scored run, and
came out **net negative — EX 53.8% → 34.5%**. The generator is back to the better-scoring
configuration. This document is the evidence, so the work can be resumed one change at a time
instead of re-derived.

| | Baseline | Experiment |
|---|---|---|
| Report | `data/benchmarks/eval_2026-07-21.json` | `data/benchmarks/eval_2026-07-21_1321.json` |
| EX (shared items) | **53.8%** (14/26) | **34.5%** (10/29) |
| spider_style | 62.5% | 50.0% |
| bird_style | 37.5% | 37.5% |
| soundwave_30 | 50.0% | 25.0% |
| idi_exec_75 | 66.7% | 22.2% |
| Blocked by verification | 3 | 0 |

Same 30-item deterministic selection, same frozen clock, greedy, seed 20260721, GTX 1650.
Over the 26 items both runs attempted: **2 improved, 7 regressed.**

---

## 1. What was changed, and why

The changes came from a failure analysis of the baseline run's 12 failures. That analysis still
stands — it is the *fixes* that failed, not the diagnosis.

| # | Change | Motivating failure |
|---|---|---|
| 1 | Forward `intent.metrics` into the SQL prompt | BIRD-003: "average track length" returned 48 raw rows; the parsed `AVG` sat unused in the envelope |
| 2 | Narrow the schema summary to the locked plan's tables | SPIDER-007: plan said `subscription_plans` alone; the emitter joined `subscriptions` and read `s.has_downloads`, a column only visible in the full 19-table dump |
| 4 | Render coded values as filter instructions (`'banned' is users.status = 2`) rather than a map to invert | BIRD-008 emitted `WHERE status = 'banned'` against an integer column — valid SQL, silently 0 rows |
| 5 | Structured SQL emission (SQL_HARDENING_PLAN Step 2) | 3 of 12 failures were invalid identifiers the grammar makes unsayable |
| — | Planner prompt: minimal tables, no junction tables, project only what was asked | Planner over-selection, found while validating #5 |

## 2. What the measurement showed

### Improved (2)

| Item | Before | After |
|---|---|---|
| SPIDER-005 | `users AS T1 JOIN users AS T2 ON T1.user_id = T2.referred_by_user_id` — 12 rows, expected 40 | Correct, 40 rows |
| BIRD-007 | Blocked: `no such column: user_follows_artists.referred_by_user_id` | Correct |

Both were exactly the class structured emission targets. The mechanism works.

### Regressed (7) — two root causes

**Cause A — a bug in the renderer's literal quoting (3 items).** The model supplies values
pre-quoted (`'album'`), because that is what SQL looks like; `_quote` wrapped them again and escaped
the inner quotes, producing `'''album'''`. Valid SQL, matches nothing, returns 0 rows, nothing
errors.

| Item | Emitted |
|---|---|
| SPIDER-003 | `WHERE albums.album_type = '''album'''` → 0 rows, expected 19 |
| BIRD-001 | `WHERE payments.payment_status = '''completed'''` → 0, expected 420 |
| SW-Q04 | `WHERE play_events.event_type = '''play'''` → 0 rows |

**This is fixed** in `backend/app/agents/sql_emitter.py` (`_quote` strips one balanced quote layer)
and pinned by `tests/test_sql_emitter.py::test_already_quoted_values_are_not_quoted_twice`. The fix
is in the tree; it was never measured, because the module is now unwired.

**Cause B — structured emission makes a wrong plan binding (4 items).** This is the real finding.

| Item | Question | Before (free-form) | After (structured) |
|---|---|---|---|
| SPIDER-002 | "How many tracks are there?" | `SELECT COUNT(*) FROM tracks` → 48 | `COUNT(track_artists.track_id) FROM track_artists JOIN tracks` → **49** |
| EXEC-002 | "How many tracks are in the catalogue?" | same, 48 | same, 49 |
| EXEC-004 | "How many artists do we carry?" | `COUNT(artist_id) FROM artists` → 12 | `COUNT(artist_genres.artist_id) FROM artist_genres JOIN artists` → **27** |
| EXEC-006 | "Average track length in minutes?" | `AVG(trk_dur_ms/60000.0) FROM tracks` → 3.5852 | `AVG(tracks.trk_dur_ms)/60000.0 FROM tracks JOIN track_artists` → 3.5776 |

In every case the **planner** chose a junction table it did not need. Free-form generation quietly
ignored that plan and wrote the simple query. Structured emission executes the plan faithfully — and
a junction table fans rows out, so every count and average computed over it is wrong by exactly the
duplication factor.

`SQL_HARDENING_PLAN.md` §"Why this order" predicted this in as many words:

> a wrong edge in `join_tree()` output is a suggestion; after Step 2 it is the query

The prerequisite was read as being about *join edges*. It applies identically to *table selection*,
and table selection was never validated the way the join vocabulary was in Step 0.

### Also observed, not scored

- **The `expressible` flag was pulled on 100% of queries** in the first attempt. It was the first
  required property in the JSON schema, and llama.cpp emits keys in declaration order — so the model
  had to rule on the query's difficulty *before composing any of it*, and always said "too hard".
  Renaming it `needs_advanced_sql` and moving it last fixed this completely (0% → structured
  emission firing on 5/5 probes). **Property order in a GBNF-compiled schema is load-bearing.**
  The hardening plan's risk register anticipated this ("rationale first in the schema (2e)"); the
  implementation omitted the `rationale` field entirely, which is the most likely remaining cause of
  the quality gap — a small model that fills slots without composing a rationale first has no
  chain-of-thought.
- Structured emission produced **zero invalid identifiers** across every probe and the whole run —
  it does what it claims. Blocked items went 3 → 0.
- The 3B model fills an unfamiliar JSON object *worse* than it writes SQL, which it has seen
  millions of times. That is the core tension and it is not obviously fixable by prompt work.

---

## 3. What is in the tree now

**Reverted** (working tree = baseline behaviour; the experiment is in commit `d8de1d3`):

- `backend/app/agents/sql_generator.py` — back to baseline: no `sql_emitter` import, original
  `PLAN_SYSTEM_PROMPT`, original `_build_schema_summary`, no metrics line, no structured branch.
- `tests/test_sql_prompt_grounding.py` — deleted; it pinned the reverted rendering.

**Kept, unwired:**

- `backend/app/agents/sql_emitter.py` + `tests/test_sql_emitter.py` (32 tests) — the renderer, with
  the quote fix and yes/no flag coercion. Nothing imports it; it is a tested building block.
- `settings.structured_sql` (`IDI_STRUCTURED_SQL`, default **False**) — now dead config until
  re-wired, documented with this measurement.
- `SqlCandidate.structured` and the orchestrator's `structured` event payload — additive,
  always `False` today.
- `llm_service.chat_with_meta(..., extra=...)` — additive; grammar-constrained calls need metadata
  for tokens/sec.

---

## 4. The methodological mistake, stated plainly

**Five changes were measured as one bundle, so none of them can be attributed.** Fixes 1, 2 and 4 are
individually plausible and cheap, and the run says nothing about them: they were confounded with a
change (structured emission) large enough to swing EX by 19 points on its own. The bundle is why the
result is un-actionable beyond "revert".

The isolating run — fixes 1/2/4 on, structured emission off — was prepared but not executed.

---

## 5. If this is resumed, in this order

1. **Measure fixes 1, 2 and 4 alone** (~35 min). They are prompt-only, and the diffs are in `d8de1d3`.
   One run tells you whether the cheap changes were ever the problem.
2. **Fix planner table selection** before re-enabling structured emission. The concrete defect: for
   single-entity questions the planner adds junction tables (`track_artists`, `artist_genres`). A
   deterministic guard is plausible — if the question names exactly one table (`_linked_tables`
   already computes this) and the extra plan tables are junctions (all columns are PK/FK, no
   descriptive attributes), prune them — but it needs its own offline tests and its own measurement.
3. **Add a leading `rationale` field** to the emission schema before re-testing structured emission,
   per SQL_HARDENING_PLAN §2e. Property order proved to be load-bearing once already.
4. **Then** re-enable `IDI_STRUCTURED_SQL=1` and re-measure, reporting structured-path coverage (how
   many items actually took it) beside EX, as §2d of the hardening plan requires.

Residual failure classes the baseline still has, from the original analysis and untouched by any of
this:

- **Domain knowledge, not grammar** — EXEC-005 counts every row of `play_events` instead of
  filtering `event_type='play'` (1230 vs 963). No schema constraint teaches this; it belongs to the
  survey/Context Manager, and the project has decided not to feed the corpus's BIRD-style `evidence`
  strings (see `data/benchmarks/README.md`).
- **Projection width** — SW-Q01/SW-Q02 return fewer columns than the reference. §3.2.2 of the
  protocol fails a column-count mismatch by design (Spider evaluator behaviour), and §0.2 freezes
  that algorithm.
- **The repair loop recovered 0 of 3 blocked items.** See `REPAIR_LOOP_PLAN.md`.
