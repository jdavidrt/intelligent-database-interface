# SQL Hardening — Join-Graph Correctness, Sampling Determinism & Structured Emission
## Interlude Plan (pre/parallel to Day 4)

**Goal:** make join- and identifier-hallucination *structurally impossible* in the SQL Generator's
final emission call, the way the constrained-decoding plan step (2026-07-19 Interlude) already made
it impossible in table/edge selection — and remove the sampling variance that makes any of this hard
to measure.

**Second, equally weighted goal (added this revision):** make the verification chain reason over the
*same* join vocabulary the generator is handed, in both directions. Today it does not: the prompt,
the planner and the verifier each hold a slightly different answer to "is this join legal", and the
verifier rejects several classes of perfectly correct SQL — an aliased CTE, an ON clause carrying a
filter alongside its key, a legal query that happens to be on one line. Those false rejections are
reproduced with exact SQL in §0. Constraining the generator harder while the verifier keeps bouncing
valid output would raise the regeneration rate without raising accuracy, so this half is a
prerequisite for the other half being measurable at all.

**Position in the sprint:** this is a second unscheduled hardening interlude, same category as
"Interlude — Schema Grounding" in `MASTERPLAN.md` §5 (between Day 3 and Day 4). It touches
`SQLGenerator` / `LLMService` / `JoinGraph` / `VerificationAgent` / `config.py` — nothing in the
`DBConnector` protocol — so it is connector-agnostic: everything here lands and gets measured on the
file connector today and carries forward unchanged when Day 4 swaps in `MySQLConnector`. It does not
block, and is not blocked by, Day 4.

**Gate:** Step 0's regressions are green — `payments↔users` and `playlists↔tracks` both resolve to
real FKs, and the **legal-SQL corpus (0j) passes verification with zero rejections** (no false
positives from the semantic or sanity layers); `IDI_STRUCTURED_SQL=true` and greedy sampling both
land; on the expanded join-heavy stress set (Step 4), structured emission produces **zero**
hallucinated-join / hallucinated-identifier verifier rejections, and the A/B report
(`data/benchmarks/`) shows the delta against the free-text baseline on the same set — reported
alongside the **false-rejection count on the legal corpus, which must stay at 0**; `pytest tests/`
stays fully green (101 → ~135); VRAM stays < 3.5 GB if Step 6 is attempted.

**Non-goal (explicitly out of scope):** EC-02 (business-term → coded value) and EC-07
(`daily_artist_metrics` vs. `play_events`) are knowledge gaps, not grammar gaps — no schema or
sampling change teaches the model *which* legal table is the right one. Don't expect this work to
move the raw EC-01…EC-08 pass count; measure it against the narrower hallucination-only metric in
Step 4 instead. EC-02/EC-07 stay LoRA-training territory (`MASTERPLAN.md` §8).

---

## Why this order

**Step 0 must land before Step 2, and it is not optional.** Structured emission promotes the join
tree from a *prompt hint the model may ignore* to the *mandatory FROM/JOIN skeleton*. Today a wrong
edge in `join_tree()` output is a suggestion; after Step 2 it is the query. Six real defects across
`join_graph.py`, `sql_generator.py` and `verification.py` (found while validating this plan — every
one reproduced against the live soundwave profile, evidence inline in §0) would therefore be
**amplified, not caught**, by structured emission. Fix the vocabulary first.

**Half of Step 0 is about the verifier, not the generator, and that half is the higher-value half.**
The three parties that consult the "closed join vocabulary" today — the prompt
(`_build_schema_summary`'s "Join paths (complete list)"), the planner (`JoinGraph.join_tree`) and
the verifier (`JoinGraph.has_edge` + rule 4b) — **do not agree with each other**, and the verifier
additionally rejects SQL that is perfectly legal. Two of those false rejections are live in `main`
today and are reproduced with exact SQL in 0f and 0h. Every false positive costs a regeneration
round-trip on a 3B model and, when the regeneration also fails, surfaces to the user as a wrong
answer with a confidently wrong didactic explanation — the worst possible outcome for a system whose
stated purpose is teaching. A verifier that is stricter than the vocabulary the generator was handed
is not "fail-safe"; it is a second, quieter hallucination source.

The rule this section enforces, and the thing to check any future change against:

> **One vocabulary, one function.** "Is this equality a legal join?" must be answered by exactly one
> piece of code (`JoinGraph`), and the prompt, the planner and the verifier must all call it — and
> must all get the *same answer*. Any place where one of the three re-derives that answer
> independently — a regex, a hardcoded string, a narrower list rendered into the prompt — is a bug
> waiting for a query to expose it.

The next section states that rule precisely, as four invariants with a test each; §0 is then just
the list of places the code currently violates them, and the fix menu after it is the set of ways
to stop.

**Step 1 (sampling determinism) has to land before structured emission is A/B'd**, not just because
it's cheap: at `temperature=0.2` the free-text baseline is itself noisy (the flip you saw — pass on
attempt 1, fail twice on identical prompts — is exactly this). Comparing a noisy baseline against a
new code path attributes sampling luck to the code change. Greedy decoding removes that confound, and
as a side effect it also stabilizes the `evaluate.py` numbers going into any report.

One consequence worth flagging up front: **once decoding is greedy, repeating the same probe query no
longer produces variance** (that's the point — identical prompt, identical output, every time). So
Step 4's stress test can't reuse "run EC-08 five times" as a methodology anymore; it has to vary the
*phrasing* of join-heavy questions instead. That's why Step 4 proposes a paraphrase set rather than
repeated trials.

Dependency graph: `0 → 2 → 3 → 4`; `1 → 4`; `5` after `4`; `6` independent.
Within Step 0: `0a → 0b → 0d` (the vocabulary must be right before it is rendered);
`0e`, `0g`, `0h` are independent of each other and of `0a`, and each is shippable on its own;
`0i` last and optional; `0j` alongside all of them.

---

## The vocabulary contract — one answer, three callers

Everything in Step 0 is a violation of this contract, so state it once, explicitly, and make it
testable. It is the design rule this interlude adds to the project; the individual fixes are just
its consequences.

**The authority.** `JoinGraph`, constructed from `DBProfile.relationship_edges`, is the *only* thing
in the system that decides join legality. It is pure, deterministic, dependency-free and cheap
enough to build per request. Nothing else may hold a second opinion — not a regex, not a hardcoded
string, not a list rendered into a prompt from a different source.

**The questions, and the one function that answers each.** Any new caller asks through this API and
nothing else. Two of the four entries are added by this interlude:

| Question | Function | Added by |
|---|---|---|
| Is `a = b` a legal join equality? | `JoinGraph.has_edge(a, b)` | exists |
| How do I connect this set of tables? | `JoinGraph.join_tree(tables)` / `.path(a, b)` | exists |
| Does this column participate in any FK? | `JoinGraph.is_key_column(col)` | **0g** |
| What do I *tell the model* is legal? | `JoinGraph.legal_equalities_for(tables)` | **0d** (fix menu option B) |

**The three callers, and what each does with the answer:**

| Caller | Where | Asks | Consequence of a wrong answer |
|---|---|---|---|
| **Prompt** | `_build_schema_summary`, `sql_generator.py:120-126` | "what is legal?" (rendered as text) | Model is instructed to write illegal SQL, or forbidden from writing legal SQL |
| **Planner** | `_constrained_plan` + `join_tree` fallback, `sql_generator.py:246, 302` | "connect these tables" | Wrong join keys ship as a LOCKED plan the model is told to copy verbatim — and, after Step 2, as the mandatory FROM/JOIN skeleton |
| **Verifier** | rule 4b, `verification.py:253-317` | "is this equality legal?" | False positive → wasted regeneration, then a wrong answer with a confident explanation. False negative → garbage results with a passing verification chain |

**The four invariants.** Each is mechanically checkable, and each maps to a real defect below —
which is the point: these are not aspirational principles, they are the failures already in the tree,
generalised so the next one gets caught by a test instead of by a user.

| # | Invariant | Meaning | Enforced by | Violated today by |
|---|---|---|---|---|
| **V0** | The vocabulary is *correct* | Every edge in `JoinGraph` corresponds to a real schema relationship, and no real one is missing | Fixture assertions on known FK/non-FK pairs (0j) | **0a** (self-loop classes invent edges), **0b** (right pair, wrong label) |
| **V1** | Planner ⊆ Verifier | Every edge `join_tree` emits must satisfy `has_edge`. The system must never plan SQL its own verifier would reject | Property test over many table sets (0j) | holds today — pin it before Step 2 makes plans binding |
| **V2** | Prompt ⊇ Planner | Every edge the planner can emit must be presented to the model as legal. Never say "this does not exist" and "copy this verbatim" about the same string | Property test: every `join_tree` edge is either in the rendered FK list or annotated in the plan block (0j) | **0d** (57 of 86 legal equalities are declared nonexistent) |
| **V3** | Verifier ⊇ Rules | SQL that follows every rule the prompt states must pass verification. The verifier may not enforce rules that were never stated | The legal-SQL corpus (0j) — a gate, not a suite | **0e** (CTEs), **0g** (ON-clause filters), **0h** (line breaks) |
| **V4** | Verifier ⊆ Vocabulary | No syntactic escape hatch may bypass the check. Legality is a property of the query, not of how it is spelled | The must-reject tests, extended per syntax form | **0i** (comma joins bypass rule 4b entirely) |

Read V3 carefully, because it is the one this project keeps breaking and the one with the worst
failure mode. **The verifier's authority comes entirely from the rules the generator was given.**
Rule 4b is legitimate — the prompt states it. "No CTEs", "no filter predicates inside ON", "no
single-line SQL" are not rules anywhere in `SYSTEM_PROMPT`; the verifier enforces them by accident,
against SQL that obeyed every instruction it was given. There is no feedback message that can fix
such a rejection, because there is nothing the model did wrong — so the regeneration loop burns a
full generate + 3-layer verify and then fails again the same way.

The practical test for any future verifier change: **name the prompt rule it enforces.** If you
can't point at one, either add the rule to `SYSTEM_PROMPT` first, or don't add the check.

---

## Step 0 — ✅ COMPLETE (2026-07-20) — One vocabulary: correctly built, symmetrically enforced

> **As built.** All of 0a–0j landed, plus **0k** (below), which the plan did not anticipate — the
> legal-SQL corpus found it within minutes of first running, which is the clearest argument for
> having written the corpus first. `pytest tests/`: **104 → 177 passed, 6 skipped**, `ruff`/`black`
> clean on every touched file. Two deviations from the plan as written, both recorded in place:
>
> - **0i took menu option A** (reject implicit-join syntax) rather than the WHERE-anchoring
>   alternative — it enforces a rule `SYSTEM_PROMPT` already states, in ~15 lines instead of ~40.
> - **0k (new): the read-only guard was duplicated, and both copies were wrong.**
>   `_layer_sanity` and `FileConnector.execute_read` each carried
>   `sql.strip().upper().startswith("SELECT")`. That is simultaneously too strict (every
>   `WITH … SELECT` rejected as a non-SELECT statement — this was the *second* bug hiding behind
>   0e's CTE false positive, invisible until the first was fixed) and too lax
>   (`SELECT 1; DROP TABLE users` starts with "SELECT" and was waved through). Both now call one
>   shared `services/sql_safety.py:is_read_only()`, AST-based and failing closed. The guard is
>   strictly stronger than before *and* the verifier can no longer green-light SQL the executor
>   refuses — a parity failure the corpus caught end-to-end.
>
> Measured after the fixes: `join_tree({"playlists","tracks"})` routes through
> `playlists.playlist_id`; the EC-08 chain is byte-identical; the poisoned equivalence classes shed
> exactly **11** of 86 edges (86 → 75 legal equalities, 29 of them raw FKs).
>
> **Follow-up (2026-07-21) — the third verdict, 0c and the residual gaps.** 0c and the self-join
> gap were re-scoped rather than left silent: they are **not decidable from the schema**, so
> `VerifyReport.verdict` gained a third state — `pass` / **`caution`** / `fail` — and they now
> report as "possibly right" instead of passing invisibly. A caveat never blocks: `overall_passed`
> stays `True`, the query executes, and the caveat rides into the didactic answer. Four sources:
> ambiguous junction bridge (0c), self-join direction, join sides the verifier cannot resolve
> (gap 4), and an extra key-column equality alongside a real FK (gap 3 — implementable precisely
> after all, since the discriminator is `is_key_column`, so it never fires on the legal
> filter-in-ON corpus). `JoinGraph.ambiguous_bridges()` exposes the ties `_score` used to break
> silently; a new per-DB survey key `join_preferences` lets a human settle a route where the domain
> has one right answer (seeded with exactly one entry — the EC-08 bridge — leaving
> `playlists↔tracks` deliberately ambiguous). Two more findings en route: the **test fixture built
> a profile production never uses** (`introspect()` without the survey, so glossary / coded values /
> join preferences were empty — now mirrors `ContextManager`), and survey `_comment` keys were
> arriving as real domain knowledge (they reach the SQL Generator's prompt via `glossary`) — now
> stripped at load. **177 → 208 tests.**

**Files:** `backend/app/services/db/join_graph.py`, `backend/app/agents/verification.py`,
`backend/app/agents/sql_generator.py`, plus regressions in `tests/test_schema_grounding.py`,
`tests/test_verification.py` and a new legal-SQL corpus (0j).

Two halves, both blocking:

| | Defect | Direction | Live in `main`? |
|---|---|---|---|
| **0a** | Self-referencing FKs poison the union-find classes | false **negative** (illegal joins accepted) + wrong plans | yes |
| **0b** | `_edge_label` prefers a derived edge over the real FK | wrong plans | yes |
| **0c** | Junction tie-break picks a semantically wrong bridge | wrong plans | yes (out of scope, recorded) |
| **0d** | Prompt's "complete list" is narrower than the plan shipped in the same prompt | contradictory instructions | yes |
| **0e** | Query-local names (CTEs) checked against the schema table list | false **positive** | yes |
| **0f** | Alias resolution — correct today, unpinned | — (pin it) | n/a |
| **0g** | Secondary non-key equality in an ON clause flagged as an invented join key | false **positive** | **yes** |
| **0h** | Sanity's aggregate-in-WHERE regex rejects legal single-line SQL | false **positive** | **yes** |
| **0i** | Comma joins bypass rule 4b entirely | false **negative** | yes |
| **0k** | Read-only guard duplicated in verifier + connector; both copies wrong in both directions | false **positive** *and* false **negative** | **yes — unplanned, found by the corpus** |

Everything below was reproduced against the live soundwave profile
(`FileConnector("soundwave").introspect()`, 19 tables, 29 FK edges) before being written down.

### 0a. Self-referencing FKs poison the union-find equivalence classes

`__init__` calls `self._union(src, tgt)` for **every** FK edge, including the three self-referencing
ones — confirmed against the live profile, these are exactly:

```
genres.parent_genre_id  -> genres.genre_id
users.referred_by_user_id -> users.user_id
playlists.forked_from_id  -> playlists.playlist_id     # note: forked_from_id, not forked_from_playlist_id
```

That merges the *role* column into the same class as the *identity* column, so every user-FK column
in the schema becomes "join-legal" against `users.referred_by_user_id`. Measured:

```
class of users.user_id = {
  payments.user_id, play_events.user_id, playlists.user_id, subscription_periods.user_id,
  subscriptions.user_id, user_follows_artists.user_id, user_liked_tracks.user_id,
  users.referred_by_user_id, users.user_id
}
JoinGraph.has_edge("payments.user_id", "users.referred_by_user_id") -> True   # should be False
```

Three consequences, all live today:

1. `_add_derived_edges` materialises `payments.user_id = users.referred_by_user_id` as a graph edge.
2. The verifier's rule-4b check accepts that equality as legal — a **semantic-layer false negative**:
   a query joining payments to the *referrer* of a user passes verification silently.
3. **The planner ships a poisoned edge into the prompt** — this is the one that actually costs
   answers today, and it is stronger evidence than the `payments` case because it is a *plan*, not
   just a permissive `has_edge`:

   ```
   join_tree({"playlists", "tracks"})
     before: ['play_events.playlist_id = playlists.forked_from_id',   # WRONG — the fork column
              'play_events.track_id = tracks.track_id']
     after 0a: ['play_events.playlist_id = playlists.playlist_id',    # correct
                'play_events.track_id = tracks.track_id']
   ```

   Any "tracks in / played from a playlist" question is currently handed a join key that filters on
   the fork lineage column instead of the playlist identity — silently returning near-empty results,
   with a *passing* verification chain, because rule 4b accepts its own poisoned vocabulary.

**Fix:** a self-loop FK is a real adjacency edge but never a class merge.

```python
for src, tgt in edges:
    ...
    self._edge_keys.add(frozenset((src.lower(), tgt.lower())))
    # A self-referencing FK (users.referred_by_user_id -> users.user_id) is a
    # *role* edge, not an identity: merging the two columns into one class would
    # make every user-FK column in the schema join-legal against the referrer
    # column, and _add_derived_edges would materialise that as a real join path.
    # The direct edge above stays legal; only the transitive closure is denied.
    if s_table != t_table:
        self._union(src.lower(), tgt.lower())
```

Verified after the fix (same live profile), so the change is provably surgical:

```
has_edge("payments.user_id", "users.referred_by_user_id") -> False   # was True
has_edge("genres.parent_genre_id", "genres.genre_id")     -> True    # direct self-loop still legal
join_tree({"artists","play_events"}) -> unchanged (EC-08 chain byte-identical)
join_tree({"playlists","tracks"})    -> fixed, see above
```

### 0b. `_edge_label` prefers a derived edge over the real FK

`_edge_label` returns `sorted(labels)[0]` — pure lexicographic. With 0a unfixed, `payments↔users`
offers both labels and `'payments.user_id = users.referred_by_user_id'` sorts before
`'payments.user_id = users.user_id'`. Verified end-to-end:

```
join_tree({"users", "payments", "subscription_plans"})
  before: ['payments.user_id = users.referred_by_user_id', ...]   # WRONG
  after 0a: ['payments.user_id = users.user_id', ...]             # correct
```

0a alone fixes the observed case, but the preference is cheap insurance for any schema where a
derived edge and a real FK connect the same table pair. Keep the original FK edge set separate from
the derived one and sort real-FK-first:

```python
self._fk_edge_keys: set[frozenset[str]] = set()   # originals only; _edge_keys gains derived too

def _edge_label(self, table_a: str, table_b: str) -> str | None:
    labels = [lbl for nxt, lbl in self._adj.get(table_a, []) if nxt == table_b]
    if not labels:
        return None
    def rank(lbl: str) -> tuple[int, str]:
        a, b = (s.strip().lower() for s in lbl.split("=", 1))
        return (0 if frozenset((a, b)) in self._fk_edge_keys else 1, lbl)
    return min(labels, key=rank)   # real FK first, then lexicographic (stable)
```

### 0c. Junction tie-break can pick a semantically wrong bridge — ✅ RESOLVED AS A KNOWN ISSUE (caveat)

> **As built (2026-07-21).** Not fixed — **declared undecidable and surfaced.** There is no faithful
> truth to recover: the right bridge depends on the question, which the FK graph never sees.
> `JoinGraph.ambiguous_bridges(a, b)` returns the tied routes, and the verifier reports
> `verdict == "caution"` naming the route taken and the alternatives. `join_preferences` in the
> per-DB survey settles a pair when the domain does have one right answer. The analysis below stands
> as the rationale.

`join_tree({"playlists", "tracks"})` routes through `play_events`, not `playlist_tracks` — both are
junction tables, both paths are length 2, so `_score`'s lexicographic tie-break decides
(`play_events` < `playlist_tracks`). **0a does not change this** (verified: after the fix the route
is still `play_events.playlist_id = playlists.playlist_id`, just with the right column) — 0a fixes
*which column*, not *which bridge*. For "which tracks are in playlist X" the membership bridge is
the right one; for "which tracks were played from playlist X" the event table is. This is a
knowledge question the FK graph cannot answer, so it stays out of scope here — but record it, because
structured emission makes the choice binding. If Step 4 shows it costing rows, the lever is
`04_soundwave_survey.json` (`source_of_truth`), not the tie-break.

### 0d. The prompt's "complete list" is narrower than the plan shipped in the same prompt

This is the vocabulary split, and it is the root cause the rest of §0 keeps rediscovering.
`_build_schema_summary` renders only the **29 raw FK edges** under a line that says, verbatim:

> Join paths (complete list — every JOIN's ON clause MUST be one of these equalities; **a join key
> not listed here does NOT exist**)

But `JoinGraph` recognises **86** legal equalities (29 FK + 57 derived/transitive), and `join_tree`
freely emits the derived ones. Measured:

```
join_tree({"artists", "play_events"}):
  track_artists.artist_id = artists.artist_id      in the prompt's "complete list"? True
  play_events.track_id = track_artists.track_id    in the prompt's "complete list"? False   <-- !
```

So on the single most important query shape in this project, the prompt tells the model, in the same
message: *"a join key not on this list does not exist"* and *"copy these ON clauses verbatim"* — for
a key that is not on the list. A 3B model resolving that contradiction is exactly the failure mode
this whole interlude exists to remove, and it does it while the verifier (which uses the 86-edge
vocabulary) would have accepted the derived edge all along.

**Do not fix this by dumping all 86 edges into the prompt.** Tripling that line buries the 29 real
FKs the model needs most and burns context on transitive shortcuts it will rarely pick unaided.
Fix the *wording* and the *locality* instead:

1. `_build_schema_summary` keeps listing the FK edges, but stops claiming exclusivity in a way the
   planner contradicts:

   > Foreign keys (the schema's real relationships): …
   > Any JOIN's ON clause must be one of these, **or one of the equivalences listed in the query
   > plan below** — those are shortcuts through a shared key and are equally valid. Any other join
   > key does not exist.

2. The LOCKED-plan block (and the "Precomputed join plan" fallback block) labels any edge it emits
   that is *not* a raw FK, so the exception is visible exactly where it is used:

   ```python
   fk_labels = {f"{s} = {t}" for s, t in profile.relationship_edges}
   for edge in plan["join_on"]:
       suffix = "" if edge in fk_labels else "   (shortcut through a shared key — equally valid)"
       plan_lines.append(f"    {edge}{suffix}")
   ```

Both the prompt text and the plan annotation derive from the same `JoinGraph`/`relationship_edges`
pair the verifier consults, so there is no third place to keep in sync.

### 0e. Query-local names are not schema tables (CTE false positive)

`_layer_semantic`'s first check walks `tree.find_all(exp.Table)` and rejects any name not in
`DBProfile` (`verification.py:157-163`). sqlglot represents a CTE *reference* as an `exp.Table`, so
the name the query itself introduced is checked against the schema. Reproduced end-to-end:

```sql
WITH top AS (
  SELECT ta.artist_id, COUNT(*) n FROM track_artists ta
  JOIN play_events pe ON pe.track_id = ta.track_id GROUP BY ta.artist_id)
SELECT a.name FROM artists a JOIN top ON top.artist_id = a.artist_id LIMIT 10;
```
```
_layer_semantic -> passed=False   "Hallucinated table: 'top' not in DBProfile"
```

This is precisely the shape of the bug the user flagged — a **scope-local binding** (a CTE name, and
by the same logic a derived-table alias) being resolved against the *schema* namespace, so a query
whose tables are all real gets reported as referencing a table that "does not exist". It also blocks
the entire CTE idiom, which is the natural way to express several EC cases (rank-then-filter, top-N
per group) and the one the model reaches for when a query needs two aggregation stages.

**Fix** — collect the names the query binds and exempt them:

```python
# Names the query binds itself (CTEs) are scope-local, not schema objects:
# `WITH top AS (...) ... JOIN top ON ...` must not be reported as a
# hallucinated table. Table ALIASES are already safe (see 0f) because
# exp.Table.name is the table, not the alias — but a CTE reference has no
# separate "real table" to fall back on, so it has to be exempted by name.
cte_names = {c.alias_or_name.lower() for c in tree.find_all(exp.CTE)}
for tbl in tree.find_all(exp.Table):
    name = tbl.name.lower()
    if name and name not in known_tables and name not in cte_names:
        return LayerResult(passed=False, message=f"Hallucinated table: '{tbl.name}' not in DBProfile")
```

Verified: `{c.alias_or_name for c in parse_one(q, dialect="mysql").find_all(exp.CTE)} == {"top"}`.
The rest of the layer already handles CTEs correctly — `traverse_scope` maps the CTE alias to a
non-`exp.Table` source, so `_scope_output_columns` supplies its projection as the column universe,
and rule 4b skips it (`l_table is None`). Only the flat table sweep was wrong.

Derived tables (`JOIN (SELECT ...) sub ON ...`) were checked too and already pass — sqlglot doesn't
emit an `exp.Table` for the alias. No change needed there; pin it anyway (0j).

### 0f. Alias resolution is correct today — pin it so it stays correct

The explicit concern: does `FROM artists AS a ... a.name` make the verifier look for a table named
`a` and declare `artists` invalid? **No, and the reason is worth writing down** so nobody
"simplifies" it into a bug later:

```
parse_one("SELECT 1 FROM artists AS a", dialect="mysql") -> exp.Table
  .name  == 'artists'      # what the table check reads
  .alias == 'a'            # never reaches the schema-membership check
```

and the column check never touches the schema namespace directly either — it resolves the qualifier
through `scope.sources`, which sqlglot keys by **alias when there is one, table name otherwise**
(`verification.py:172-183`). Confirmed passing end-to-end on the fully aliased EC-08 shape:

```sql
SELECT a.name, COUNT(*) FROM artists AS a
JOIN track_artists AS ta ON ta.artist_id = a.artist_id
JOIN play_events  AS pe ON pe.track_id  = ta.track_id
GROUP BY a.name LIMIT 10;                       -- semantic: PASS, sanity: PASS
```

Rule 4b is alias-safe by the same mechanism: it maps each qualifier back through
`sources.get(lq)[0]` to the **real** table name before asking `has_edge` (`verification.py:287-292`),
which is why the error messages can say `artists.artist_id` while the SQL said `a.artist_id`.

Two consequences for this step:

- **Never add an alias-aware "fix" here.** Any patch that starts checking `tbl.alias` against
  `known_tables`, or that resolves qualifiers with a regex instead of `traverse_scope`, reintroduces
  exactly the failure being guarded against. The comment above the table check should say so.
- **Pin it with regressions** (0j), including the nastiest variant — an alias that *shadows a
  different real table's name*:

  ```sql
  SELECT tracks.event_id FROM play_events AS tracks LIMIT 5;   -- 'tracks' is an alias for play_events
  ```

  Verified: `sources` maps `tracks -> ("play_events", play_events' columns)`, so `tracks.event_id`
  resolves against `play_events` and passes — the alias correctly shadows the real table inside its
  scope. A regex-based resolver would resolve it against the real `tracks` table and reject it.

### 0g. Rule 4b flags a secondary non-key predicate as an invented join key (live false positive)

`_find_illegal_join_edge` walks **every** `exp.EQ` inside an ON clause and requires each one to be an
FK edge (`verification.py:279-316`). But an ON clause routinely carries a join key *plus* a filter
equality, and the filter is not a relationship. Both of these are legal SQL and both are rejected
today:

```sql
SELECT a.name, al.title FROM artists a
  JOIN albums al ON al.artist_id = a.artist_id AND al.label = a.label LIMIT 10;
-- semantic: FAIL "Invented join key: 'al.label = a.label' ... no foreign key links
--                 albums.label to artists.label"

SELECT t.title FROM tracks t
  JOIN albums al ON al.album_id = t.album_id AND al.release_date = t.release_date LIMIT 5;
-- semantic: FAIL, same shape
```

The first equality in each is the real FK; the verifier never looks at it because it rejects on the
second. The surface is not exotic — the live schema has ten column names shared by two or more
tables with no FK between them (`country`, `country_code`, `status`, `label`, `title`, `name`,
`release_date`, `created_at`, `monthly_price`, `is_prim`), and "same artist **and** same label",
"same day **and** same country" are ordinary analytical predicates.

**Fix — check the join, not the equality.** A JOIN is anchored if *at least one* of its
column-to-column equalities is a legal edge; the remaining equalities are filters and are none of
rule 4b's business. This is both stricter and looser than today in exactly the right places:

```python
# A JOIN's ON clause carries at most one relationship and any number of
# filters (`... ON al.artist_id = a.artist_id AND al.label = a.label`).
# Requiring EVERY equality to be an FK edge rejected legal SQL (0g);
# requiring at least ONE still catches the invented-key failure this rule
# exists for, because an invented key is the join's ONLY equality.
for join in joins:
    eqs = _cross_table_equalities(join.args.get("on"), sources)   # [(a, b, node), ...]
    if not eqs:
        continue                       # ON with no column-to-column equality (rare, e.g. ON 1=1)
    if any(graph.has_edge(a, b) for a, b, _ in eqs):
        continue                       # anchored — the rest are filters
    # Unanchored: report the most key-like equality, for the best message.
    a, b, node = max(eqs, key=lambda e: (graph.is_key_column(e[0]) + graph.is_key_column(e[1])))
    return _invented_join_key_result(a, b, node, graph)
```

with one small addition to `JoinGraph`, so "is this a key column" is answered from the same object
as "is this a legal edge" rather than re-derived in the verifier:

```python
# __init__:  self._key_columns.add(src.lower()); self._key_columns.add(tgt.lower())
def is_key_column(self, qualified: str) -> bool:
    """True when this column participates in any FK edge in the schema."""
    return qualified.lower() in self._key_columns
```

Check the primary target still gets caught — it does, because an invented key is the join's *only*
equality: `ON a.artist_id = pe.user_id` has one equality, `has_edge` is False, so the join is
unanchored and rejected with the same message and the same legal-chain hint as today. Same for the
`da.artist_id = pe.track_id` regression in `test_schema_grounding.py`.

Residual gap accepted on purpose: `ON a.name = u.name` as the *only* equality between two tables is
now still rejected (unanchored, correct), but a hallucinated key hiding *alongside* a real FK is
accepted. That is the right trade — the extra key can only narrow the result set, never fabricate a
relationship, whereas the false positive it removes costs a full regeneration round-trip.

### 0h. Sanity's aggregate-in-WHERE regex rejects legal SQL (live false positive)

Already described in 2g as a structured-emission concern — it is **not**; it is live today and it
fires on hand-written and model-written SQL alike. Reproduced on `main`:

```sql
SELECT a.name FROM artists a JOIN track_artists ta ON ta.artist_id=a.artist_id
WHERE a.name IS NOT NULL GROUP BY a.name HAVING COUNT(*) > 5 LIMIT 10;
-- single line -> sanity FAIL "Aggregate function found in WHERE clause — use HAVING instead"
-- same query, one clause per line -> sanity PASS
```

A verifier whose verdict depends on where the newlines are is not a verifier. `WHERE … HAVING
COUNT(*)` is the canonical shape for every "…with more than N…" question, and `WHERE … ORDER BY
COUNT(*) DESC` for every "top N in the last N months" question — i.e. the regex misfires on the two
most common answer shapes in the project the moment the SQL arrives on one line.

The fix moves here from 2g — but **not verbatim, because the version drafted in 2g introduces a new
false positive of its own.** `tree.find_all(exp.Where)` + `walk()` descends into subqueries nested
inside the WHERE, where an aggregate is perfectly legal:

```sql
SELECT u.user_id FROM users u
WHERE u.user_id IN (SELECT p.user_id FROM payments p GROUP BY p.user_id HAVING COUNT(*) > 5)
LIMIT 10;
```
```
naive AST walk  -> finds COUNT(*)      => would reject  (new false positive)
scope-limited   -> finds nothing       => passes        (correct)
genuine `WHERE COUNT(a.artist_id) > 5` -> scope-limited finds it  => rejects (correct)
```

All three lines above were run. The check must therefore be limited to the WHERE's **own** scope —
stop descending at any nested `exp.Select`/`exp.Subquery`:

```python
def _own_scope_aggregates(where: exp.Where) -> list[exp.AggFunc]:
    """Aggregates belonging to THIS WHERE, not to a subquery inside it.
    `WHERE x IN (SELECT ... HAVING COUNT(*) > 5)` is legal SQL: the aggregate
    lives in the subquery's scope, where HAVING is exactly the right place."""
    out = []
    for node in where.walk():
        if not isinstance(node, exp.AggFunc):
            continue
        parent, nested = node.parent, False
        while parent is not None and parent is not where:
            if isinstance(parent, (exp.Select, exp.Subquery)):
                nested = True
                break
            parent = parent.parent
        if not nested:
            out.append(node)
    return out
```

That this trap existed in the first draft is itself the argument for the legal-SQL corpus (0j):
a "fix" for a false positive is exactly as likely to ship a new one, and only a standing corpus of
known-good SQL catches that. Add the nested-subquery case to it as entry #13.

Do this **before** Step 2 so the Step 4 A/B can't attribute the pre-existing bug to structured
emission — that mis-attribution is the concrete cost of leaving it where it was. 2g keeps only the
"emit one clause per line" note, which becomes cosmetic once this lands rather than load-bearing.

### 0i. Comma joins bypass rule 4b entirely (false negative — do last, and carefully)

The mirror image of 0g. `_find_illegal_join_edge` reads `expression.args["joins"]`, so an
implicit-join query has nothing to walk. Reproduced:

```sql
SELECT a.name FROM artists a, play_events pe WHERE a.artist_id = pe.user_id LIMIT 5;
-- semantic: PASS   <-- the exact invented key that rule 4b exists to reject
```

The generator's prompt asks for explicit `JOIN` syntax, so this is not a hot path — but it is a
hole in the "closed vocabulary" claim, and it is the kind of hole a regeneration loop finds by
accident when the explicit-JOIN form keeps getting rejected.

**Preferred fix — enforce the rule that already exists.** `SYSTEM_PROMPT` asks for explicit `JOIN`
syntax, so rejecting implicit joins enforces a *stated* rule (V3-clean) in ~8 lines and closes the
hole completely, instead of reimplementing rule 4b a second time over WHERE:

```
LayerResult(passed=False, message=(
    "Implicit (comma) join: write each relationship as an explicit "
    "JOIN ... ON so its join key can be verified — e.g. "
    "FROM artists JOIN play_events ON <one of the listed join paths>."))
```

The message is actionable, which matters: unlike 0e/0g/0h, this rejection tells the model something
it can actually do differently, so the regeneration loop converges instead of looping.

**Thorough alternative, if Step 4 shows those rejections costing answers** — apply the *same
anchored-join test* from 0g to comma-separated sources, using WHERE equalities as the candidate set,
with two guards against turning a false negative into a false positive:

1. Only consider a table pair that has **no legal equality anywhere in the WHERE**; a pair with one
   legal equality is anchored and every other predicate between those tables is a filter.
2. Only report a pair when **both** of the offending equality's columns are `is_key_column` — a
   comma-join whose only cross-table predicate is `users.country = artists.country` is a deliberate
   non-key correlation, not a hallucinated FK, and rejecting it would be a new false positive of
   exactly the kind 0g just removed.

See the fix menu for the full option set. If neither shape feels safe, **skip 0i**: it is the only
item in §0 that is not blocking, and shipping it wrong costs more than not shipping it. Record the
gap in the risk register either way.

### 0k. (NOT PLANNED — found by the corpus) The read-only guard was duplicated, and both copies were wrong

The plan did not predict this one. It surfaced the first time the legal-SQL corpus ran, as a second
failure on the CTE entry *after* 0e had already been fixed — a bug that was structurally invisible
while 0e was masking it.

Two independent copies of the same safety rule:

```python
# verification.py, _layer_sanity
if not sql_upper.lstrip().startswith("SELECT"): ...reject
# file_connector.py, execute_read
if not sql.strip().upper().startswith("SELECT"): raise ValueError(...)
```

Wrong in **both** directions at once:

| SQL | String guard | Correct | |
|---|---|---|---|
| `WITH top AS (…) SELECT …` | rejected | read-only | too strict — blocks every CTE query |
| `SELECT 1; DROP TABLE users` | **passed** | must reject | too lax — starts with "SELECT" |
| `SELECT … UNION SELECT …` | passed | read-only | correct by luck |
| `WITH t AS (…) DELETE FROM users` | rejected | must reject | correct by luck |

And because the two copies lived on opposite sides of the pipeline, fixing only the verifier's copy
produced a *new* failure mode — verification passing SQL that `execute_read` then refuses:

```
verify(WITH … SELECT …).overall_passed -> True
execute_read(same sql)                 -> ValueError: Only SELECT statements are permitted.
```

**Fix:** one shared `backend/app/services/sql_safety.py`, following the precedent
`services/temporal.py` already sets (shared by generator and verifier "so generation and
verification can never drift apart"):

```python
_READ_ONLY_TYPES = (exp.Select, exp.SetOperation)

def is_read_only(sql: str, dialect: str = "mysql") -> bool:
    """True when `sql` is a single read-only statement. Fails closed."""
    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception:
        return False
    return isinstance(tree, _READ_ONLY_TYPES)
```

`parse_one` returns `exp.Block` for stacked statements and the concrete write type
(`exp.Delete`/`exp.Update`/`exp.Drop`) for writes, including behind a CTE — so a single
`isinstance` decides all four rows of the table correctly. Both call sites now import it, and the
corpus asserts parity in both directions (every legal query executes; every read-only-guard
rejection also raises in `execute_read`).

**The lesson, for the risk register:** V3 and V4 violations can *hide each other*. 0e's CTE
rejection masked 0k's CTE rejection completely — the corpus entry stayed red after the first fix
and named a different layer, which is the only reason it was found. A single-assertion smoke test
("does the CTE query pass?") would have been marked green by whichever fix landed second.

### 0j. Regressions + the legal-SQL corpus

**Join-graph regressions** (`tests/test_schema_grounding.py`):
`has_edge("payments.user_id", "users.referred_by_user_id")` is False while
`has_edge("payments.user_id", "users.user_id")` stays True; the direct self-loop edge
`genres.parent_genre_id = genres.genre_id` stays legal; `join_tree({"users","payments",
"subscription_plans"})` contains `payments.user_id = users.user_id`;
`join_tree({"playlists","tracks"})` contains `play_events.playlist_id = playlists.playlist_id` and
**not** `playlists.forked_from_id`; the EC-08 chain (`artists`/`play_events`) is byte-identical to
before the fix. Confirm the existing 13 schema-grounding tests still pass — verified locally that 0a
leaves the EC-08 and artists/genres/play_events trees unchanged.

**Vocabulary-parity regressions** — one test per invariant from "The vocabulary contract" above.
These are the tests that make the contract real rather than aspirational; write them as properties
over many table sets, not as fixed examples:

```python
ALL_SETS = [set(c) for n in (2, 3) for c in combinations(TABLE_NAMES, n)]   # ~1k sets, all cheap

def test_v1_planner_never_plans_what_the_verifier_rejects(graph):
    """V1: Planner ⊆ Verifier."""
    for tables in ALL_SETS:
        tree = graph.join_tree(tables)
        if tree is None:
            continue
        for edge in tree[0]:
            a, b = (s.strip() for s in edge.split("=", 1))
            assert graph.has_edge(a, b), f"planner emitted an edge rule 4b rejects: {edge}"

def test_v2_every_planned_edge_is_declared_legal_to_the_model(graph, soundwave_profile):
    """V2: Prompt ⊇ Planner — an edge is either in the rendered FK list or
    carries the 'shortcut through a shared key' annotation (0d)."""
    ...

def test_v0_known_relationships(graph):
    """V0: spot-check the vocabulary against ground truth — the FK pairs that
    must be legal and the plausible-looking pairs that must not."""
    ...
```

V1 would have caught 0a's poisoned edge; V2 is the standing guard on 0d; V3 is the legal-SQL corpus
below; V4 is the must-reject set. Together they are the answer to "how do we know the three parties
still agree" six months from now, when the MySQL connector introspects a different schema.

**The legal-SQL corpus** (new, `tests/test_verification_false_positives.py`): a list of
hand-written, unambiguously **correct** queries against the soundwave schema that must ALL pass
`_layer_semantic` and `_layer_sanity`. This is the artifact that turns "no false positives" from an
aspiration into a gate. Seed it with everything reproduced above, then grow it every time a real
false rejection is found:

| # | Shape | Guards |
|---|---|---|
| 1 | Fully aliased 3-table EC-08 chain | 0f |
| 2 | Alias shadowing another real table's name (`play_events AS tracks`) | 0f |
| 3 | Unaliased joins, fully qualified (`_assemble_sql`'s own output shape) | 2f |
| 4 | CTE + join back to a real table | 0e |
| 5 | Derived table (`JOIN (SELECT …) sub ON …`) | 0e |
| 6 | Correlated subquery referencing an outer alias | scope chain |
| 7 | ON with FK **and** a secondary non-key equality (`al.label = a.label`) | 0g |
| 8 | Single-line `WHERE … HAVING COUNT(*) > N` | 0h |
| 9 | Single-line `WHERE … ORDER BY COUNT(*) DESC` | 0h |
| 10 | Legal self-join (`genres child JOIN genres parent`) | 0a, rule 4b self-join skip |
| 11 | Multi-hop chain using a *derived* edge (`play_events.track_id = track_artists.track_id`) | 0d |
| 12 | `SELECT DISTINCT` + `LEFT JOIN` with a NULL-safe `IS NULL` filter | EC-11 regex |
| 13 | `WHERE x IN (SELECT … HAVING COUNT(*) > N)` — aggregate legal inside the subquery | 0h's own fix |

Keep the corpus paired with its opposite — the existing "must be rejected" tests
(`test_semantic_rejects_invented_join_key_between_real_columns`, `WHERE COUNT(x) > 5`,
`; DROP TABLE`). A change that makes the corpus pass by making the rejection tests fail has not
fixed anything; both files must be green together, and Step 4 reports both numbers.

---

## Step 0 fix menu — what to try, and what to fall back to

The subsections above each prescribe one fix. This is the menu behind those choices: for every
defect, the approaches worth trying, in the order worth trying them, with the reason each one might
not survive contact with the code. Written because 0h's own first draft shipped a new false positive
(see 0h) — the first idea for a verifier fix is not reliably the right one, and having the
alternatives written down is cheaper than rediscovering them at 2 a.m.

**Rules for working this menu:**
1. Land one option, run the corpus (0j) **and** the must-reject set, then move on. Never batch two
   verifier changes into one commit — when the corpus goes red you want one suspect.
2. If the recommended option fails, take the next one down; don't invent a fifth in the moment.
3. Anything marked ✗ is a *recorded rejection* — it was considered and is wrong. Don't re-propose it.

### 0a — self-loop FKs poison the equivalence classes

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Skip `_union` when `s_table == t_table`; keep the direct edge in `_edge_keys` | 3 lines | very low | **try first** — already verified end-to-end (EC-08 unchanged, `playlists↔tracks` fixed) |
| B | Keep the union, but tag classes born from a self-ref column and skip them in `_add_derived_edges` | ~15 lines | low | fallback if some other consumer turns out to need the merged class |
| C | Model roles as distinct nodes (`users#referrer` vs `users#identity`) throughout the graph | large | medium | correct in general, and the only thing that would let 2d's self-join guard be dropped — but out of scope here; note it as the long-term shape |
| ✗ | Filter self-ref FKs out of `relationship_edges` at introspection | — | — | breaks EC-04 self-joins and the direct-edge legality test in 0j; the edge is real, only the *transitive closure* is wrong |

### 0b — `_edge_label` prefers a derived edge over the real FK

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | `_fk_edge_keys` set + `rank()` sorting real FKs first, lexicographic within | ~8 lines | very low | **try first** — cheap insurance independent of 0a |
| B | Don't create a derived edge at all when a real FK already connects the same table pair | ~4 lines | medium | simpler, but wrong for a schema with two distinct relationships between one pair (two FK columns from A to B); soundwave has none today, MySQL introspection on Day 4 may |
| ✗ | Order `_adj` by insertion and take the first | — | — | order becomes dependent on introspection order — silently unstable across connectors, which is exactly what Day 4 changes |

### 0c — junction tie-break picks a semantically wrong bridge

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Leave it; document; revisit only if Step 4 shows it costing rows | 0 | — | **try first** — it is a knowledge gap, and §Non-goal says knowledge gaps aren't solved by grammar |
| B | `source_of_truth` in `04_soundwave_survey.json` maps concept → preferred bridge; `_score` consults it | ~20 lines + data | low | the right lever *if* it turns out to matter; per-DB and declarative, no code change for a new database |
| ✗ | Keyword heuristic on the question ("played" → `play_events`, "contains" → `playlist_tracks`) | — | — | a hardcoded second opinion about join semantics living outside `JoinGraph` — a direct violation of the vocabulary contract |

### 0d — prompt's "complete list" is narrower than the plan it ships

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Reword the join-paths line to admit plan shortcuts + annotate non-FK edges in the plan block | ~10 lines | very low | **try first** — zero context cost, fixes the contradiction where it is read |
| B | `JoinGraph.legal_equalities_for(plan["tables"])` — render the FK list plus only the derived edges *among the planned tables* (a handful, not 57) | ~20 lines | low | escalate here if the model still refuses to use annotated plan edges; also gives the contract its fourth API entry |
| ✗ | Render all 86 equalities in the schema summary | — | — | measured: 29 → 86 lines, burying the FKs the model needs most; the closed-list framing works *because* it is short |
| ✗ | Drop the "complete list" claim | — | — | that framing is what fixed hallucinated tables in the 2026-07-19 interlude; weakening it trades a known win for an unknown one |

### 0e — CTE names checked against the schema table list

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Collect `{c.alias_or_name for c in tree.find_all(exp.CTE)}` and exempt those names | ~4 lines | very low | **try first** — verified: returns `{"top"}` on the repro; handles `WITH RECURSIVE` for free since the name is still bound |
| B | Drive the table check from `traverse_scope` instead of the flat `find_all(exp.Table)` sweep — scope already distinguishes CTE sources from real tables | ~25 lines | medium | more principled and would cover nested/shadowed CTE scopes properly; take it if A proves leaky on a real query |
| C | Run `sqlglot.optimizer.qualify` first and check the qualified tree | ~10 lines | medium-high | rewrites the SQL before checking, so error messages stop matching what the user sees in the didactic panel — a real cost for a teaching tool |
| ✗ | Add CTE names to `known_tables` for the whole verify pass | — | — | leaks the exemption into the *column* checks too, so a hallucinated column on a CTE stops being caught |

### 0g — secondary non-key predicate in ON flagged as an invented join key

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Per-JOIN anchoring: legal if **any** cross-table equality in the ON is an FK edge | ~25 lines | low | **try first** — keeps every existing rejection green (an invented key is the join's only equality) while removing the whole false-positive class |
| B | Skip any equality where either side fails `is_key_column` | ~3 lines | low | much simpler; use it if A's grouping gets fiddly. Weaker: `ON a.name = u.name` as a *sole* join predicate would stop being caught |
| A+B | A for the verdict, B for choosing which equality to name in the message | — | — | what 0g actually specifies — B alone loses the good error message |
| ✗ | Only check the first equality in the ON clause | — | — | order-dependent; `ON al.label = a.label AND al.artist_id = a.artist_id` would flip the verdict |
| ✗ | Restrict rule 4b to equalities whose columns end in `_id` | — | — | a naming convention is not a schema; breaks on any DB whose keys aren't named that way, i.e. probably Day 4's |

### 0h — aggregate-in-WHERE regex

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Scope-limited AST walk (`_own_scope_aggregates`, 0h) | ~15 lines | low | **try first** — the naive version was *tested and rejected*: it flags legal `WHERE x IN (SELECT … HAVING COUNT(*))` |
| A′ | Same, plus pass the tree parsed in `_layer_semantic` into `_layer_sanity` instead of parsing a third time | +10 lines | low | worth doing together — `verify()` currently parses the same SQL twice; wiring it once removes the chance the two layers ever disagree about what they're checking |
| B | Keep the regex, bound it to stop at `GROUP BY`/`HAVING`/`ORDER BY`, add `re.DOTALL` | ~3 lines | high | tempting and wrong: still blind to subqueries, still string-shaped. Only if sqlglot is somehow unavailable in that path — it isn't |
| ✗ | Normalise the SQL to one clause per line before the regex | — | — | makes the verdict depend on a formatter; the same bug wearing a hat |

### 0i — comma joins bypass rule 4b

| | Approach | Effort | Risk | |
|---|---|---|---|---|
| **A** | Reject implicit-join syntax outright with a didactic message ("use explicit `JOIN … ON`") | ~8 lines | low | **try first, and it may be all you need** — the prompt already mandates explicit JOINs, so this enforces a *stated* rule (V3-clean) and closes the hole completely. Cost: rejects legal-but-unrequested SQL, so it must go in the corpus as a deliberate rejection, not a false positive |
| B | Apply 0g's anchored-pair test to WHERE equalities, with both guards from 0i | ~40 lines | medium | the thorough version; only worth it if A's rejections show up in Step 4 as a real cost |
| C | Rewrite comma joins into explicit joins with sqlglot before checking | ~10 lines | medium | elegant if a transform exists that is reliable across dialects; verify before committing to it — otherwise you inherit a rewriting bug in the safety layer |
| **D** | Do nothing; record in the risk register | 0 | low | fully acceptable — 0i is the only non-blocking item in §0 |

### Where each fix goes if it doesn't work

If an option lands and the corpus goes red in a way the menu didn't anticipate, the fallback is
always the same and it is not "loosen the check until it passes": **write the failing SQL into the
corpus first**, then decide whether the verifier or the generator is wrong. A corpus entry added
before the fix is a regression test; one added after is a rationalisation.

---

## Step 1 — Sampling determinism (#2)

**Files:** `backend/app/config.py`, `backend/app/services/llm_service.py`, `backend/app/agents/sql_generator.py`

1. Add two settings, same pattern as `constrained_planning` (`config.py:39-43`):

   ```python
   # SQL sampling determinism — greedy decoding for both SQL-Generator LLM
   # calls (constrained plan + final emission). Run-to-run variance at
   # temperature>0 was observed to flip a query from pass to fail on
   # identical prompts; eliminating it is also a precondition for
   # meaningfully A/B-ing IDI_STRUCTURED_SQL below (see "Why this order").
   # Clarification/query-understanding prose keeps its own temperatures —
   # determinism is a SQL-generation property, not a whole-pipeline one.
   sql_temperature: float = Field(default=0.0, alias="IDI_SQL_TEMPERATURE")
   sql_top_k: int = Field(default=1, alias="IDI_SQL_TOP_K")
   ```

2. `LLMService.chat_with_meta` (`llm_service.py:98-103`) has no `extra` passthrough today — `chat()`
   does (`llm_service.py:85-91`). Add the same parameter, mirroring the "additive, `chat()` stays
   byte-identical" precedent from Day 3's `chat_with_meta` addition:

   ```python
   def chat_with_meta(
       self,
       messages: list[dict[str, str]],
       temperature: float = 0.3,
       timeout: int = 90,
       extra: dict[str, Any] | None = None,
   ) -> tuple[str, dict[str, Any]]:
       data, elapsed = self._request(messages, temperature, timeout, extra)
       ...
   ```

   Note `_request` already forwards `extra` unconditionally (`llm_service.py:67-73`) — this is a
   two-line signature change, nothing deeper.

3. Two call sites in `sql_generator.py`:
   - Plan step (`_constrained_plan`, the `llm_service.chat(...)` call, currently `sql_generator.py:211-217`, `temperature=0.1`): switch to `temperature=settings.sql_temperature` and fold sampling into the existing `extra` dict alongside `response_format`.
   - Final emission (`generate`, the `llm_service.chat_with_meta(...)` call, currently `sql_generator.py:357`, `temperature=0.2`): switch to `temperature=settings.sql_temperature` and pass the same `extra`.

   ```python
   _GREEDY = {"top_k": settings.sql_top_k, "top_p": 1.0, "min_p": 0.0}
   ...
   raw = llm_service.chat(
       messages, temperature=settings.sql_temperature, timeout=60,
       extra={"response_format": {"type": "json_object", "schema": schema}, **_GREEDY},
   )
   ...
   raw, self.last_meta = llm_service.chat_with_meta(
       messages, temperature=settings.sql_temperature, extra=_GREEDY,
   )
   ```

4. **Smoke-test before wiring broadly — and test the right thing.** `top_k`/`top_p`/`min_p` are
   llama.cpp server extensions to the OpenAI-shaped payload. The failure mode is *not* a 4xx: an
   unrecognised field is silently ignored, so **a 200 proves nothing**. Verify the effect, not the
   acceptance:

   - Send the *same* high-entropy prompt (e.g. "write a haiku about databases") twice with the greedy
     `extra` and confirm the two completions are byte-identical; then twice with `temperature=0.8`
     and confirm they differ. Identical-then-different is the only evidence that matters.
   - Cross-check `llama_server.log` for the per-request sampler-params line, which echoes the values
     the server actually applied.

   Residual caveat worth writing into the harness output: llama.cpp is only deterministic per
   *sampler*; batching and KV-cache reuse can still perturb logits at the margin. `start.py` launches
   `llama-server` with no `--parallel`/`-np` flag (`start.py:176-181`), so it defaults to a single
   slot and this is a non-issue today — but if `-np > 1` is ever added, greedy stops implying
   byte-identical, and Step 4's methodology has to be revisited.

5. Leave `clarification.py` (temperatures 0.0/0.2/0.3/0.3/0.4) and `query_understanding.py`
   (`temperature=0.1`) untouched — this step is scoped to SQL generation specifically, per the
   analysis's own framing ("keep some temperature only for clarification/didactic prose").

This alone should fix the observed flakiness and is safe to ship independently of everything below.

---

## Step 2 — Structured SQL emission prototype (#1)

**Files:** `backend/app/agents/sql_generator.py`, `backend/app/agents/verification.py`, `backend/app/config.py`, `backend/app/models/envelope.py`, `backend/app/services/orchestrator.py`

### 2a. Config flag

```python
# Structured SQL emission (prototype, default off). When true, the final
# generation call asks for JSON (select/where/group_by/having/order_by/limit)
# instead of free-text SQL, and the FROM/JOIN skeleton is assembled in
# Python from the locked plan — never written by the model. A join the
# model never writes is a join it can't hallucinate. WHERE/HAVING/ORDER BY
# stay free strings (see 2e) but remain covered by the existing verifier,
# same as today's free-text path.
structured_sql: bool = Field(default=False, alias="IDI_STRUCTURED_SQL")
```

### 2b. Unify the two plan sources into one shape

`generate()` currently has two independent paths that each know about "which tables, which joins":
the constrained-decoding plan (`_constrained_plan`, returns a `dict` whose `"tables"` is a **sorted
list**, not a set — `sql_generator.py:243-250`) and the deterministic `_linked_tables` +
`JoinGraph.join_tree` fallback (`sql_generator.py:297-310`, today only *injects text into the
prompt*, returns nothing structured). Structured emission needs one table set no matter which path
produced it, so the fallback branch must build the same `{tables, join_on, output_columns}` shape
instead of only formatting a string. This is a real refactor, not cosmetic — everything past this
point assumes a single `plan` variable regardless of source.

### 2c. Attach-order anchor + a completeness guard

`join_tree()` returns `(edges, connected_tables_as_a_set)` (`join_graph.py:186-222`); `plan["tables"]
= sorted(all_tables)` then discards attach order. Rendering valid SQL needs `FROM <anchor> JOIN <next>
ON <edge> ...`, and a naive `plan["tables"][0]` as the anchor is **wrong in general**: the re-sorted
list can put a pulled-in intermediate alphabetically before the table `join_tree` actually started
from. Measured: `join_tree({"artists","genres","play_events"})` returns tables sorted as
`['artist_genres', 'artists', ...]`, but the traversal started at `artists`.

Capture the anchor *before* calling — no change to `join_tree`'s return shape (existing tests pin it
down with exact tuple equality):

```python
anchor = sorted(t.lower() for t in tables if t)[0]   # == join_tree's internal wanted[0]
tree = JoinGraph(profile.relationship_edges).join_tree(tables)
...
data["anchor"] = anchor
data["join_complete"] = True      # only on this branch — see below
```

**Two guards the original plan was missing:**

1. **`join_tree` can return `None`** (a required table unreachable from the rest). Today that just
   leaves the model's raw `join_on` picks in place, which is harmless when they're only a prompt
   hint. Under structured emission it is not: `_assemble_from_join` walks `join_on` only, so any
   table in `plan["tables"]` that no edge attaches **silently never appears in FROM** — and a SELECT
   referencing it then gets bounced by the semantic layer for no reason the model can act on. Set
   `join_complete = True` only when `tree is not None`, and gate structured emission on it.

2. **Replay completeness.** `_assemble_from_join` walks `join_on` starting `seen = {anchor}`; because
   `join_tree` appends each edge in the same loop iteration where it attaches the new table
   (`connected.add(b)` before the next pair is processed), exactly one side of every edge is
   guaranteed already in `seen` when you reach it, in order. That argument holds — but it depends on
   replay parity with a loop in another module, including its `label not in edges` dedupe. Don't
   trust it; assert it. `_assemble_from_join` returns `None` unless `seen == {t.lower() for t in
   plan["tables"]}` at the end, and `_generate_structured` falls through to free text on `None`.

Do all of this for **both** plan sources from 2b so `anchor` and `join_complete` are always present.

### 2d. Self-join fallback (explicit, conservative limitation)

`plan["tables"]` is a flat list of names — it cannot represent a table joined to itself in two roles
(EC-04: `genres` parent/child, `users` referrer/referred, `playlists` forked-from). Confirmed against
the live profile: those three are exactly the self-referencing tables in soundwave (the FK columns
are `genres.parent_genre_id`, `users.referred_by_user_id`, `playlists.forked_from_id`). Neither plan
source handles this today either (self-joins already only work via the free-text path, per
`test_semantic_accepts_self_join`'s literal aliased SQL). Detect and skip structured emission for
that query rather than silently producing something wrong:

```python
_SELF_REF_TABLES = {  # tables with an FK edge to themselves
    split_qualified(src)[0] for src, tgt in profile.relationship_edges
    if split_qualified(src)[0] == split_qualified(tgt)[0]
}
if _SELF_REF_TABLES & {t.lower() for t in plan["tables"]}:
    # Conservative on purpose (same rationale as _linked_tables): a query
    # that merely *mentions* genres/users/playlists without needing the
    # self-join also takes this path unnecessarily, but a wrong guess here
    # would silently produce a single-role query for a two-role question.
    plan = None  # generate() falls through to the free-text path
```

Cost to be honest about: `users`, `genres` and `playlists` are three of the most frequently mentioned
tables in the schema, so this guard will divert a *large* fraction of real questions to the free-text
path. Step 4 must report structured-path **coverage** (share of probes that actually took it)
alongside the hallucination rate — a 0 % hallucination rate over 20 % of the probes is a much weaker
result than it looks.

### 2e. JSON schema — what's enumerated vs. what stays free text

Enum universe = every `table.column` belonging to a table in the locked plan (not just
`output_columns` — GROUP BY / ORDER BY legitimately need columns the planner didn't pick as display
columns):

```python
def _locked_columns(profile: DBProfile, plan: dict) -> list[str]:
    locked = {t.lower() for t in plan["tables"]}
    return sorted(
        f"{t.name}.{c.name}" for t in profile.tables
        if t.name.lower() in locked for c in t.columns
    ) + ["*"]
```

```python
{
  "type": "object",
  "properties": {
    "rationale": {"type": "string"},          # FIRST — see "reason before you pick" below
    "distinct": {"type": "boolean"},
    "select": {
      "type": "array", "minItems": 1, "maxItems": 8,
      "items": {
        "type": "object",
        "properties": {
          "column":     {"type": "string", "enum": locked_columns},
          "aggregate":  {"type": "string", "enum": ["NONE","COUNT","COUNT_DISTINCT","SUM","AVG","MIN","MAX"]},
          "expr_suffix": {"type": "string"},   # e.g. "/60000.0" for EC-05 ms->min
          "alias":      {"type": "string"}
        },
        "required": ["column", "aggregate"]
      }
    },
    "where":    {"type": "string"},
    "group_by": {"type": "array", "maxItems": 6, "items": {"type": "string", "enum": locked_columns}},
    "having":   {"type": "string"},
    "order_by": {"type": "string"},
    "limit":    {"type": "integer", "minimum": 1, "maximum": 500}
  },
  "required": ["rationale", "select"]
}
```

Three changes from the first draft, each for a concrete reason:

- **`having` is mandatory to include, not optional.** Without it, "artists with more than N plays"
  and every other post-aggregation threshold has nowhere legal to go, and the model will put the
  aggregate in `where` — which the sanity layer rejects **100 % of the time**
  (`verification.py:377-381`). A whole EC class would fail by construction.
- **`distinct`** — EC-03's "how many *different* …" needs `SELECT DISTINCT`; `COUNT_DISTINCT` only
  covers the aggregate form.
- **`rationale` moved to the front.** llama.cpp compiles JSON Schema properties to GBNF **in schema
  order**, so property order is generation order. With `select` first, the model commits to columns
  before writing a single reasoning token — throwing away exactly the chain-of-thought advantage
  today's `### Rationale` → `### SQL` format gets for free. Putting `rationale` first restores it at
  zero cost. (Same argument applies to `_constrained_plan`, which has no free-text field at all:
  consider adding a leading `"reasoning": {"type": "string"}` there and measuring it in Step 4.)

`column`/`group_by` are enum-constrained — this is where FROM/JOIN/SELECT/GROUP BY identifier
hallucination actually gets closed off. `where`, `having`, `order_by`, `expr_suffix` stay free
strings on purpose: they carry operators and literals (`>= DATE_SUB(...)`, `DESC`, `/60000.0`) that
aren't enumerable, but any identifier smuggled inside them is **still caught** by the existing
semantic layer — `traverse_scope` covers the whole statement, not just SELECT
(`verification.py:135-262`), so this isn't a new hole, it's the same residual coverage the free-text
path already relies on today.

Known limitation to accept explicitly: `expr_suffix` appends *outside* the aggregate
(`AVG(tracks.duration_ms)/60000.0`), so `AVG(duration_ms/60000.0)` is not expressible. For EC-05
these are arithmetically equal; for a non-linear transform they would not be. Don't add an
`expr_wrap` field speculatively — note it and let Step 4 say whether it's needed.

### 2f. Deterministic assembly (`sql_generator.py`, new functions)

```python
_AGG = {
    "NONE": "{c}", "COUNT": "COUNT({c})", "COUNT_DISTINCT": "COUNT(DISTINCT {c})",
    "SUM": "SUM({c})", "AVG": "AVG({c})", "MIN": "MIN({c})", "MAX": "MAX({c})",
}

def _assemble_from_join(plan: dict) -> str | None:
    """FROM/JOIN skeleton replayed from join_tree's attach order. None when the
    replay doesn't reach every planned table (see 2c guard 2)."""
    anchor = plan["anchor"]
    clause, seen = f"FROM {anchor}", {anchor}
    for edge in plan.get("join_on", []):
        left, right = (s.strip() for s in edge.split("=", 1))
        lt, rt = left.split(".")[0].lower(), right.split(".")[0].lower()
        if lt in seen and rt in seen:
            continue  # defensive: join_tree shouldn't emit this, but never double-JOIN
        if lt not in seen and rt not in seen:
            return None  # disconnected — replay parity broken, bail to free text
        new_table = rt if lt in seen else lt
        clause += f"\n  JOIN {new_table} ON {edge}"
        seen.add(new_table)
    return clause if seen == {t.lower() for t in plan["tables"]} else None

def _assemble_sql(plan: dict, s: dict) -> str | None:
    from_join = _assemble_from_join(plan)
    if from_join is None:
        return None
    parts = []
    for item in s["select"]:
        col = item["column"]
        agg = item.get("aggregate", "NONE")
        if col == "*" and agg not in ("COUNT", "COUNT_DISTINCT"):
            agg = "COUNT"          # SUM(*)/AVG(*) are not valid SQL
        expr = _AGG[agg].format(c=col)
        expr += item.get("expr_suffix", "") + (f" AS {item['alias']}" if item.get("alias") else "")
        parts.append(expr)
    head = "SELECT DISTINCT" if s.get("distinct") else "SELECT"
    lines = [f"{head} {', '.join(parts)}", from_join]
    if s.get("where"):    lines.append(f"WHERE {s['where']}")
    if s.get("group_by"): lines.append(f"GROUP BY {', '.join(s['group_by'])}")
    if s.get("having"):   lines.append(f"HAVING {s['having']}")
    if s.get("order_by"): lines.append(f"ORDER BY {s['order_by']}")
    lines.append(f"LIMIT {s.get('limit') or 200};")
    return "\n".join(lines)
```

Two properties worth naming:

- **No table aliases.** Every reference is fully qualified `table.column` (matching the enum strings
  exactly), which sidesteps EC-01's whole "did it forget to qualify an ambiguous column" failure mode
  by construction.
- **One clause per line** — cosmetic *once 0h has landed*, and load-bearing if it hasn't (see 2g).
  It also renders better in the didactic SQL panel, which is reason enough on its own.

### 2g. Sanity-layer interaction — already fixed upstream in 0h

The first draft of this plan treated the aggregate-in-WHERE regex as a structured-emission problem
and proposed working around it by emitting multi-line SQL. That was the wrong diagnosis: the regex
is a **live false positive on hand-written and model-written SQL alike** (`WHERE … HAVING COUNT(*)`
on one line is rejected; the same query with newlines passes), so it moved to **0h** and is fixed
before Step 2 starts.

What remains here is only the reason it had to move: had it stayed, `_assemble_sql`'s output would
have failed sanity on most of its target queries, and Step 4's A/B would have reported that as a
**structured-emission regression** rather than as the pre-existing verifier bug it is. That
mis-attribution — a measurement reading a known bug as a property of the thing being measured — is
the general hazard 0e–0h exist to remove before any A/B runs.

Cross-check when 0h lands: `_assemble_sql`'s output shape (fully qualified, no aliases, one clause
per line) is corpus entry #3 in 0j, so it is verified as a *legal* shape independently of whether
structured emission is switched on.

### 2h. Wiring into `generate()`

```python
if settings.structured_sql and plan and plan.get("tables") and plan.get("join_complete"):
    candidate = self._generate_structured(intent, profile, plan, feedback)
    if candidate is not None:
        return candidate
    # falls through to the existing free-text path below on any failure
```

`_generate_structured` mirrors `_constrained_plan`'s try/except-return-None discipline: malformed
JSON, a timeout, a failed assembly guard, or an older llama.cpp all degrade to `None`, never to an
exception the pipeline has to handle specially.

**`last_meta` hygiene (easy to miss).** `generate()` sets `self.last_meta` only from the
`chat_with_meta` call on the free-text path (`sql_generator.py:357`), and the orchestrator publishes
it verbatim into the `sql_generator` "done" event (`orchestrator.py:173-177`), which `evaluate.py`
reads for tokens/sec. So: `_generate_structured` must call `chat_with_meta` (not `chat`) and set
`self.last_meta` itself, and `generate()` must reset `self.last_meta = None` on entry — otherwise a
structured attempt that fails and falls back would leave the *previous query's* metrics attached to
this one, quietly corrupting the benchmark.

Also keep populating `tables_used` / `columns_used` on the structured path — the didactic panel reads
them and they're free here (the plan already has both).

One policy choice: **on regeneration** (`feedback is not None`), skip structured emission and go
straight to free text. A structured candidate that failed verification most likely failed because the
schema didn't fit that query's shape (e.g. it needed a nested aggregate) — retrying the same
constrained schema is less likely to help than the free-text path's regeneration prompt, which
already carries the verifier's exact rejection message.

### 2i. Identifier casing

Edge labels are built from `profile.relationship_edges` **verbatim** for real FK edges
(`join_graph.py:61`) but **lowercased** for derived ones (`_add_derived_edges` reads the lowered
union-find keys), and `anchor` is lowercased, while `_locked_columns` uses `t.name` as introspected.
Soundwave's DDL is entirely lowercase so nothing breaks today — but Day 4's MySQL introspection is
where mixed-case identifiers arrive, and MySQL with `lower_case_table_names=0` (the Linux default) is
case-sensitive on table names. Normalise once, at assembly: map every table/column token through
`{t.name.lower(): t.name}` from the profile before emitting. Cheap now, silent breakage later.

### 2j. `SqlCandidate` — new field, not an overload

`generation_method` (`envelope.py:64`, `Literal["lora","base_model","fallback"]`) tracks *which
weights ran* — an orthogonal axis to *which emission format was used*. Don't overload it; add:

```python
structured: bool = False   # true when this candidate came from the JSON-emission path
```

Surface it on the `sql_generator` "done" event payload in `orchestrator.py` (next to the existing
`**(self._sql_generator.last_meta or {})`, `orchestrator.py:173-177`) so the frontend/eval harness can
tell the two paths apart in the event stream, the same way `adapter` is tracked today.

### 2k. Injection/safety note (no new defense needed)

Assembling free-text fragments (`where`, `having`, `order_by`, `expr_suffix`) into a SQL string by
concatenation looks like it opens an injection surface, but the residual risk is identical to today's
free-text path, which already lets the model write an entire SQL statement freely. Both the
three-layer verifier (syntax/sanity, including the read-only `SELECT` guard at
`verification.py:364-367`) and the connector's single-statement `execute_read` are the existing
backstop — no new defense is required here, only preserved. Worth one regression: a `where` string
containing `; DROP TABLE` must still be rejected.

---

## Step 3 — Offline tests

**File:** new `tests/test_structured_sql.py`, mirroring `test_schema_grounding.py`'s conventions
(same fixtures from `conftest.py`: `soundwave_profile`, `patched_vector_context`; same
`monkeypatch.setattr(sg_module, "llm_service", ...)` import-site pattern — note `conftest.py`'s
docstring warning: patching the *definition* site silently does nothing).

Minimum coverage:

- **Step 0 regressions** live in `test_schema_grounding.py` and the new
  `test_verification_false_positives.py` (see 0j), not here.
- Enum correctness: locked columns == exactly the plan's tables' columns, nothing from an unlocked
  table.
- `_assemble_from_join` produces a connected FROM/JOIN chain matching `join_on` for a multi-hop plan
  (reuse the EC-08 `artists`/`play_events`/`track_artists` fixture already in
  `test_schema_grounding.py`), with `artists` — not the alphabetically-first `artist_genres` — as
  anchor in the 3-table case.
- **Completeness guard:** a hand-built plan whose `join_on` omits an edge returns `None`, and
  `_generate_structured` falls back rather than emitting a table-less-FROM query.
- **`join_complete` gate:** `join_tree` returning `None` never reaches structured emission.
- Self-join tables (`users`/`genres`/`playlists`) correctly fall back to `plan = None`.
- Malformed / missing JSON from the mocked LLM degrades to the free-text path without raising.
- Regen path (`feedback is not None`) skips structured emission per 2h.
- `SqlCandidate.structured` is set correctly on both paths; `last_meta` is `None` (not stale) after a
  structured attempt that fell back.
- A `where` fragment carrying `; DROP TABLE users` is rejected end-to-end (2k).
- **`_assemble_sql`'s output survives its own verifier**: assemble a query for the EC-08 plan, run it
  through the full three-layer chain against `soundwave_profile`, assert `overall_passed`. This is
  the end-to-end statement of "generation and verification share one vocabulary" — if structured
  emission can produce SQL its own verifier rejects, one of them is wrong, and this test says which
  build it started in. (The sanity-layer regressions themselves live with 0h in
  `test_verification_false_positives.py`.)

---

## Step 4 — Live A/B measurement

**File:** new `tests/ab_structured_sql.py`, reusing `PROBES`/`run_query`/`select_db` from
`gate_d1.py` — same import pattern as `ab_harness.py`.

**Toggling — cheaper than the first draft claimed.** `ab_harness.py` toggles `registry.json`, which
`adapter_registry.activate()` re-reads from disk on every call. `structured_sql` is a `Settings`
field, so its *value* is read from the environment once at process start — but `sql_generator` reads
`settings.structured_sql` at **call** time, and pydantic-settings models are mutable by default
(`config.py:9-14` sets no `frozen=True`). So an in-process flip works:

```python
from backend.app.config import settings
settings.structured_sql = True    # takes effect on the next /query, no restart
```

That needs a small guarded debug hook (a `POST /debug/flags` endpoint gated on a dev-only setting, or
running the harness in-process against the app). If you'd rather not add a debug surface, the
two-restart pattern from `DAY4_PLAN.md` Step 4 still works — just have the harness **print the
requirement loudly and stamp the active flag value into the report**, so a forgotten restart shows up
as a duplicated run rather than a false comparison.

**Set `IDI_FREEZE_NOW`.** `play_events` seed data ends 2025-01-20, so any "last N months" probe run
against the real clock returns 0 rows and the row-count > 0 criterion below becomes meaningless.
Freeze the clock to a date inside the data window and record it in the report header.

**Probe set — expand, don't reuse EC-01…EC-08 as-is.** Two reasons: (1) EC-02/EC-07 are knowledge
gaps this work doesn't target (see Non-goal above) — mixing them into the pass count dilutes the
signal; (2) per "Why this order," greedy decoding makes repeated runs of the *same* probe pointless
post-Step-1. Add a **join-heavy paraphrase set** — 12-20 rephrasings of multi-hop questions
(EC-08-style "most played artists," "playlists containing tracks by X," genre lookups through
`track_genres` vs `artist_genres`, etc.).

**Report these six numbers, not a pass count:**

| Metric | Why |
|---|---|
| Hallucinated table/column verifier rejections | The primary target |
| "Invented join key" semantic rejections | The 2026-07-19 failure class |
| **Structured-path coverage** (% of probes that actually took it) | 2d's self-join guard diverts a lot; a clean rate over a small slice is a weak result |
| Row-count > 0 | Catches queries that are legal but answer nothing |
| **Regeneration rate** (% of probes needing a second generate) | The direct cost of a verifier false positive: every one of them buys a full extra generate + 3-layer verify on a 3B model. A hardening step that lowers rejections but raises this number has moved the problem, not solved it |
| **False rejections on the legal corpus (0j) — must be 0** | The gate. Run the corpus through the live pipeline as part of the same report, not only in `pytest`, so a config difference between the test env and the running backend can't hide a regression |

Overall EC pass count is explicitly *not* the metric for this interlude.

**Read rejection counts in pairs, never alone.** A drop in "invented join key" rejections is
ambiguous on its own: it means either the generator stopped inventing keys (the goal) or the
verifier stopped catching them (0g's change makes this a live possibility, since it loosened
per-equality checking to per-join). The legal corpus and the existing must-reject tests are what
disambiguate — report both, in the same table, every run.

---

## Step 5 (stretch, sequence last) — Best-of-N regeneration (#3)

**File:** `backend/app/services/orchestrator.py`, the single-regeneration block at
`orchestrator.py:211-241`.

Deliberately sequenced after Steps 0-4 are measured, not before: Best-of-N amplifies whatever the
generator already does, so it's cheaper to fix the structural failure class first and use Best-of-N
only to mop up genuine remaining semantic misses. Concretely: replace the current single
`self._sql_generator.generate(..., feedback=...)` + single re-verify with up to 2 candidates at
`temperature≈0.4` (candidate generation only — Step 1's greedy default stays for attempt 1), verify
each, take the first that passes, otherwise keep the most specific failure message for the user-facing
error. Note the two features compose: if structured emission is on, all candidates already share the
same locked FROM/JOIN skeleton, so Best-of-N's diversity comes only from the SELECT/WHERE fields
(and the plan step, if that's ever given temperature > 0) — still useful, just a smaller search space
than today's fully-free-text Best-of-N would explore. Also budget the latency: each extra candidate
is a full generate + 3-layer verify on a 3B model.

---

## Step 6 (independent, lowest priority) — Quantization bump (#4)

**File:** `start.py` (`MODEL_PATH`, currently hardcoded at `start.py:39-41`).

Parametrize the GGUF filename via an env var (`IDI_MODEL_FILENAME`, default the current
`qwen2.5-coder-3b-instruct-q4_k_m.gguf`) so trying q5_k_m (~2.3 GB) / q6_k (~2.6 GB) doesn't need a
code edit. Re-run `tests/evaluate.py` on both and compare `tokens_per_sec` and the accuracy summary
before adopting either — and confirm VRAM stays under the 3.5 GB budget with room for a LoRA
(`CLAUDE.md` hard constraint), since that headroom is exactly what a future trained adapter needs.
Can be done in parallel with Steps 0-5; it's orthogonal to everything else here and, per the analysis,
won't fix systematic (join/identifier) errors — only "model knew better but flubbed it" cases.

---

## File checklist

| File | Change |
|---|---|
| `backend/app/services/db/join_graph.py` | ✅ **(0a)** no `_union` on self-loop FKs; **(0b)** `_fk_edge_keys` + FK-preferring `_edge_label`; **(0g)** `_key_columns` + `is_key_column()` + `is_fk_edge()`. `legal_equalities_for()` not needed — 0d option A sufficed |
| `backend/app/agents/verification.py` | ✅ **(0e)** exempt CTE names + comment pinning why aliases are already safe; **(0g)** `_cross_table_equalities` + per-JOIN anchoring; **(0h)** `_find_aggregate_in_where`, scope-limited; **(0i)** `_find_implicit_join`; **(0k)** read-only guard delegated to `sql_safety` |
| `backend/app/services/sql_safety.py` | ✅ **new (0k)** — `is_read_only()`, the single definition of the read-only rule |
| `backend/app/services/db/file_connector.py` | ✅ **(0k)** `execute_read` calls the shared guard instead of its own `startswith("SELECT")` |
| `tests/test_vocabulary_parity.py` | ✅ **new** — 12 tests: V0 (vocabulary correctness), V1/V2 as properties over all 2- and 3-table combinations |
| `tests/test_verification_false_positives.py` | ✅ **new** — 14-entry legal corpus × (per-layer, end-to-end, executes) + 9 must-reject + executor parity = 61 tests |
| `backend/app/agents/sql_generator.py` | ✅ **(0d)** join-paths wording + `_render_join_edges` annotating non-FK edges in both plan blocks. *Still pending (Steps 1–2):* greedy sampling on both LLM calls; unify fallback plan shape; `anchor` + `join_complete`; `_locked_columns`, `_assemble_from_join`, `_assemble_sql`, `_generate_structured`; self-join guard; `last_meta` reset; casing normalisation |
| `tests/test_schema_grounding.py` | ✅ + 6 join-graph regressions (0a/0b/`is_key_column`), 13 → 19 tests |
| `backend/app/config.py` | + `sql_temperature`, `sql_top_k`, `structured_sql` settings |
| `backend/app/services/llm_service.py` | `chat_with_meta` gains `extra` param |
| `backend/app/models/envelope.py` | `SqlCandidate.structured: bool = False` |
| `backend/app/services/orchestrator.py` | surface `structured` on the `sql_generator` "done" event payload |
| `tests/test_structured_sql.py` | new |
| `tests/ab_structured_sql.py` | new |
| `.env` / `.env.example` | document new flags (all default to today's behavior — no required edits) |
| `start.py` | (Step 6 only) `IDI_MODEL_FILENAME` |

Note the shape of this table: **`verification.py` was the second-largest change in the plan**, and
five of its six edits are false-positive removals. That is the correction this revision made to the
original plan, which treated the verifier purely as a backstop to be preserved. As built, Step 0
touched five source files and added 73 tests without a single line of the structured-emission work
it was a prerequisite for.

## Known issues & caveats (as built, 2026-07-21)

Open, documented, and none blocking. Each surfaces to the user as `verdict == "caution"` rather than
passing silently or being rejected — see `tests/test_verification_caveats.py` and §3.12.6 of
`docs/reports/IDI_Capitulo3_v2.md`.

| Known issue | Status | Why it stays |
|---|---|---|
| **Ambiguous junction bridge** (0c) — `playlists↔tracks` via `playlist_tracks` / `play_events` / `user_liked_tracks` | **Known, undecidable from the schema.** Reported as caution; settleable per-DB via `join_preferences` | The correct route depends on the question, not the database. Any tie-break the graph picks is a guess wearing a uniform |
| **Self-join direction** — `genres` parent/child, `users` referrer/referred, `playlists` forked-from | **Known, unverifiable.** Reported as caution | The graph knows tables, not roles; reversing the two columns is equally legal SQL answering the opposite question |
| **Unresolvable join side** — CTE, subquery, or outer-scope alias | **Known, unverifiable.** Reported as caution | No schema table behind the alias, so rule 4b has nothing to check against. "I could not check this" ≠ "this is fine" |
| **Invented key alongside a real FK** (gap 3) | **Accepted caveat.** Anchored joins pass; the extra equality is reported as caution | Rejecting it would reinstate 0g's false positive on every legal filter-in-`ON` query. An extra equality can only narrow rows, never fabricate a relationship |
| **Implicit comma joins** | **Closed by explicit rejection** (0i menu option A) | Enforces a rule `SYSTEM_PROMPT` already states, and the message is actionable — so regeneration converges instead of looping |
| **`verify()` parses the same SQL 5×** | Open, cosmetic | Correctness unaffected; fold into Step 2 when `_layer_sanity` is touched anyway. Five parses are five chances for the layers to disagree — same drift class as 0k |
| **`tools/build_tercer_informe.py` is stale** | Guarded, not fixed | Its `BODY` is a literal snapshot; regenerating would silently drop §3.12. It now aborts if the report contains a section its `BODY` lacks |
| **Effect on answer accuracy unmeasured** | Routed to Chapter 4 (OE4) | Structural fix; quantifying it is evaluation evidence, not implementation |

## Risk register

| Risk | Mitigation |
|---|---|
| **0g loosens rule 4b (per-JOIN anchoring) and lets a real hallucinated key through alongside a legal one** | An unanchored join is still rejected, which is the only shape the observed failures took; the must-reject tests stay green next to the corpus, and Step 4 reads rejection counts in pairs so a drop can't be mistaken for progress |
| **0e's CTE exemption becomes a hallucination hole** (model invents a table and a `WITH` clause naming it) | The exemption is keyed to names actually bound by a `WITH` in the same statement — a CTE that exists is a real relation with a real projection, and `_scope_output_columns` still validates every column against it |
| **0i turns a false negative into a new false positive** (non-key comma-join correlation flagged) | Preferred option rejects implicit-join *syntax*, enforcing a rule the prompt already states, rather than re-judging join legality in WHERE; the thorough alternative keeps both guards; 0i is explicitly droppable (menu option D) |
| **A fix for a false positive ships a new one** — happened twice: 0h's first draft flagged legal `WHERE … IN (SELECT … HAVING COUNT(*))`, and fixing 0e's CTE rejection exposed 0k's identical CTE rejection one layer down | The legal-SQL corpus (0j) is the standing guard, and the fix menu's rule 1: one option per commit, corpus + must-reject set green before the next |
| **Two violations mask each other**, so a smoke test goes green on the second fix while the first bug is still live (0e ↔ 0k, both rejecting the same CTE query from different layers) | Corpus entries assert **per layer** and **end-to-end and executes**, so a still-failing entry names which layer is guilty instead of just "CTE broken" |
| **A safety rule gets duplicated again** and the copies drift (0k: verifier vs. connector) | Shared rules live in `services/` and are imported, never re-implemented — the precedent `temporal.py` set and `sql_safety.py` now follows; the corpus asserts verifier/executor parity in both directions |
| Legal-SQL corpus goes stale — new false positives ship unnoticed | Corpus is a gate, not a suite: every real false rejection found in Step 4 or in use gets appended before the fix lands |
| Self-join guard diverts most real questions to free text, making the A/B unrepresentative | Report coverage % as a first-class metric (Step 4) |
| Structured schema can't express a needed shape (nested aggregate, CASE, UNION, window fn) | `_generate_structured` returns `None` → free-text fallback; count fallbacks in Step 4 |
| GBNF property order silently costs reasoning quality | `rationale` first in the schema (2e); measure against the free-text baseline |
| Step 0 changes join semantics under the existing prompt path | Regressions pin the EC-08 chain byte-identical; verified locally before writing this plan |
| Planner, prompt and verifier drift apart again after this interlude — especially when Day 4's MySQL introspection produces a different schema | The four invariants (V0–V4) are property tests over the *live* profile, not fixed examples, so they re-run against whatever schema the connector introspects; V1/V2 fail mechanically on any divergence |
| Greedy decoding stops being byte-deterministic if `-np > 1` is ever added to `start.py` | Noted in Step 1.4; harness prints the sampler settings it observed |

## On completion

Follow the precedent already in the repo: once Steps 0-4 are green, add an "Interlude — Vocabulary
Parity, Sampling & Structured SQL Emission ✅ COMPLETE" entry to `MASTERPLAN.md` §5 (between
"Interlude — Schema Grounding" and "Day 4"), and update `CLAUDE.md`'s status header with the same
one-paragraph convention used for the 2026-07-19 entry. Not done now, since the work isn't done yet —
MASTERPLAN entries in this repo are written retrospectively, checked boxes only.
