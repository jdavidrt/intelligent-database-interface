# Repair Loop — Improvement & Evaluation Plan

**Status:** proposed, not started. Written 2026-07-21 against the first scored run.
**Scope:** `Orchestrator.run`'s verify → repair → regenerate → block path, and the evidence needed
to decide whether it is worth keeping in its current shape.

---

## 0. What exists today, and what the first run says about it

The loop lives in `backend/app/services/orchestrator.py` and has three stages:

1. **Deterministic repair** — if `verify.overall_passed` is false and the verifier produced
   `repaired_sql`, that SQL is re-verified once.
2. **One regeneration** — still failing, the failing layers' messages are concatenated into a
   `feedback` string and `SQLGenerator.generate(..., feedback=...)` runs again. The plan step reruns
   too, folding in the tables named by the verifier's legal-chain hint.
3. **Block** — still failing, nothing executes and the user gets "Verification failed."

**The measurement that motivated this plan.** In `data/benchmarks/eval_2026-07-21.json` (26 items,
greedy, frozen clock): **3 items were blocked, and regeneration recovered 0 of them.** All three were
identifier errors the verifier described correctly — `no such column: s.has_downloads`,
`no such column: explicit`, `no such column: user_follows_artists.referred_by_user_id`.

That is a 0% recovery rate on the only sample we have. It is a small sample, and the honest reading
is *"the loop is unevaluated"* rather than *"the loop does not work"* — which is precisely why the
first step below is instrumentation and not a fix.

**One thing already changed underneath it.** Structured SQL emission (SQL_HARDENING_PLAN Step 2)
landed on 2026-07-21, and per that plan's §2h regeneration deliberately **skips** structured emission
and falls back to free-form. So the loop now retries on the *weaker* of the two paths. That policy
was written before structured emission existed to be measured; §R3 revisits it.

---

## 1. Why not just "retry more"

Two reasons a bigger retry budget is the wrong first move:

- **A rejection may be the verifier's fault, not the generator's.** `EVALUATION_PROTOCOL.md` §4.4
  makes hard FPR — legal SQL given verdict `fail` — a mandatory companion metric, and
  `tests/test_verification_false_positives.py` exists because five such false positives were real and
  shipped. Retrying a correct query harder does not make it more correct; it burns 30–90 s and then
  blocks it anyway. **Classifying rejections has to precede tuning the response to them.**
- **Every retry is charged to the latency contract.** §5 sets P50 < 5 s (GPU) as the threshold and
  < 3 s as the target. The observed end-to-end P50 is 87.6 s, so latency is already the project's
  most-violated number; a second regeneration adds a full generation to the worst cases, which are
  exactly the ones already furthest over budget.

---

## R0. Instrument the loop (prerequisite — no behaviour change)

Nothing here changes what the system does. It changes what we can see.

**Backend.** The orchestrator already yields `verification` `progress` events for "Repair applied"
and "Verification failed (…) — regenerating SQL once…", but as prose. Attach a structured payload
instead: `{attempt, stage, failing_layer, failing_rule, repaired: bool, recovered: bool}`.

**Harness.** `evaluation/run.py` records per item:

| Field | Meaning |
|---|---|
| `first_verdict` | verdict of the *first* verification, before any repair |
| `repair_applied` | deterministic repair fired |
| `regenerated` | regeneration fired |
| `recovered` | a later attempt passed after the first failed |
| `first_failure_layer` | syntax / semantic / sanity |
| `emission` | structured / free_form, per attempt |

**New reported figures**, as diagnostics beside EX — not as protocol metrics (see §R5):

```
Recovery rate      = recovered / (items whose first verification failed)
Repair yield       = recovered by deterministic repair / repairs attempted
Regeneration yield = recovered by regeneration        / regenerations attempted
Loop cost          = mean added wall time on items that entered the loop
```

**Gate:** re-run the 30-item selection. EX must be unchanged within noise — a behaviour-neutral change
that moves EX means the instrumentation is not neutral, which is worth knowing immediately.

---

## R1. Classify every rejection before changing anything

For each first-verification failure in the instrumented run, hand-label one of:

| Class | Meaning | Where the fix belongs |
|---|---|---|
| **A** | Real generator error, and the message describes it correctly | The repair loop (R2–R4) |
| **B** | Real generator error, but the message is vague or misleading | The verifier's message (R2) |
| **C** | The SQL was legal — a verifier false positive | `tests/test_verification_false_positives.py` corpus, then the verifier. **Not** the repair loop |

Class C items are hard-FPR events and must be counted as such under §4.4. Shipping a repair-loop
improvement while class C is non-empty would be optimising the recovery from a bug we should be
deleting instead.

**Deliverable:** a table of every rejection with its class, committed alongside the run. This is the
input to every decision below; none of R2–R4 should start before it exists.

---

## R2. Make the rejection actionable (class B only)

Today `feedback` is `"; ".join(layer.message ...)` plus a generic instruction block. The generator
therefore receives prose and has to parse the failure out of it.

**Change:** have each verification layer return a structured rejection —
`{layer, rule, offending_identifier, legal_alternatives}` — and render the feedback from that. Rule 4b
already names the legal chain and should be the template for the rest.

**Offline test (no LLM):** for every entry in the must-reject corpus, assert the rejection names the
offending identifier and, where one exists, at least one legal alternative. A rejection that cannot
name what was wrong cannot be expected to produce a corrected query.

---

## R3. Route the retry to the stronger path, not the weaker one

SQL_HARDENING_PLAN §2h sends every regeneration to free-form. Split it by failure class instead:

| First failure | Retry with | Why |
|---|---|---|
| Invalid identifier / illegal join key | **structured** | The grammar makes the same mistake unsayable. The three blocked items in the pilot were all this class |
| Aggregate in WHERE, GROUP BY shape, needs subquery/CTE/window | **free-form** | The structured schema cannot express the fix, so retrying it is guaranteed to fail the same way |
| Verifier false positive (class C) | **neither — do not retry** | Fix the verifier; retrying wastes a generation and blocks a correct answer either way |

Implement as one pure function `retry_strategy(failure) -> "structured" | "free_form" | "none"`,
unit-tested offline against the must-reject corpus. Keeping the decision in a pure function is what
makes it testable without a model.

---

## R4. Choose the retry budget from data

Only after R1–R3. Measure attempts ∈ {1, 2} on the same selection and report:

- recovery rate at each budget,
- added P50 and P90 latency on items that enter the loop,
- EX delta.

Decide with the numbers and record the decision and its date. A second attempt is worth having only
if its marginal recovery justifies a full extra generation against a latency contract already being
missed by an order of magnitude.

---

## R5. Where these numbers may and may not be reported

`EVALUATION_PROTOCOL.md` is frozen (§0.2) and its metric contract is closed. Recovery rate is a
**generator** diagnostic and is not one of its metrics:

- **May** be reported in `data/benchmarks/eval_*.md` as a diagnostic, and cited in Chapter 4 as
  supporting analysis.
- **May not** be added to the protocol's metric set, given a threshold, or used to reframe EX.
- The one figure that already belongs to the protocol is the **blocked-item count**, reported as EDR
  events under §3.4/§4, and **hard FPR** under §4.4 — which is where class C items land.

---

## Gate

- Rejection classification table exists and class C is empty (or every class C item has a failing
  regression test committed against it).
- Recovery rate reported with its denominator visible — the sample is small enough that a rate
  without an `n` beside it is misleading.
- Hard FPR on the legal-SQL corpus stays 0.
- EX does not regress on the 30-item selection.
- Latency delta stated explicitly, not omitted because it is unflattering.

## Non-goals

- **Best-of-N regeneration** — that is SQL_HARDENING_PLAN Step 5 and a different mechanism.
- **Any threshold change in `EVALUATION_PROTOCOL.md`.**
- **Making the loop recover more by loosening the verifier.** A higher recovery rate bought with a
  weaker verifier is a worse system that reports better numbers, which is the failure mode the whole
  evaluation apparatus exists to prevent.
