# Day 2 — Frontend Rebuild (No Tailwind) & Visualization
## IDI Implementation Plan (v2, realigned 2026-07-02)

**Goal:** The didactic UI — a learner sees the reasoning, the schema, the chart, and the lesson. Backed entirely by the Day 1 pipeline on the file connector.

**Gate D2:** A non-SQL user runs a query end-to-end in the browser, sees live per-agent progress (including which adapter/instruction profile each agent ran on), a rendered chart, and the plain-language "why" as a distinct panel from the SQL and the results. Bundle scan confirms zero Tailwind artifacts.

**Pre-condition:** Gate D1 passed — `/query`, `/ws`, `/session`, and `/db/profile` are live against `SoundwaveFileConnector`.

> **Realignment note.** The original v2 draft of this file assumed Day 2 starts from an empty `frontend/src/`, ported wholesale from `legacydocs/DAY3_PLAN_v1.md`. That's no longer true: the **sandbox detachment** (2026-07-02, see `CLAUDE.md`) already repointed the sandbox's chat UI at the live `/query` pipeline as a side effect of deleting `sandbox/`, so a working — but pre-didactic — chat frontend already exists in `frontend/src/`. Day 2's real job is narrower than "build the frontend": **evolve the working chat MVP into the componentized, didactic architecture** the masterplan describes, not start from zero. The step map below reflects what's actually in the tree today.

---

## Current Baseline (what's already in `frontend/src/`)

Carried over verbatim from the sandbox during detachment, then lightly adapted to the agent pipeline:

| File | State | Notes |
|---|---|---|
| `App.tsx` | Working | Single-page chat + a `benchmarks` tab toggle (local `useState`, no router, no Zustand) |
| `components/Header.tsx` | Working | Nav tabs (Chat / Benchmarks) + theme cycler button |
| `components/ChatBox.tsx`, `MessageBubble.tsx`, `InputArea.tsx`, `TypewriterMessage.tsx`, `GeneratingIndicator.tsx` | Working | Free-text chat loop, ported from `sandbox/frontend/src/` unchanged |
| `components/AgentProgress.tsx` | **New in Day 1's detachment, not in the original plan** | Renders live agent steps *inline in the chat feed* as a collapsed list (icon + label + message per agent, in first-seen order). Does **not** render `payload.adapter` yet |
| `components/BenchmarksPage.tsx` | Working | Legacy `/chat` + `/benchmark` loop UI, carried from sandbox; unrelated to the `/query` pipeline |
| `utils/queryClient.ts` | Working | `streamQuery()` — `fetch()` + NDJSON line-parsing over `POST /query`; **not** the `/ws` WebSocket route. `buildResultHTML()` assembles teaching summary + SQL + results table into **one HTML blob** injected via `MessageBubble`, not four distinct panels |
| `utils/sqlHighlighter.ts`, `utils/markdownRenderer.ts` | Working | Ported verbatim, already wired into `buildResultHTML()` |
| `index.css` | Working | Raw CSS (not CSS Modules), ~1100 lines, 5 complete theme palettes switched via `[data-theme]` + a `theme-btn` cycler — this already **is** the glass-theme port the original Step 2 called for, just not tokenized/modularized |
| `stores/`, `services/`, `styles/` | **Empty (placeholder `README.md` only)** | Directories exist per the canonical layout but hold no code |
| `package.json` | No `recharts`, no `zustand` | Only `react`/`react-dom` + Vite/TS tooling |

Backend surface already available to build against (confirmed in `backend/app/api/routes/`):

- `POST /query` — NDJSON stream of `AgentEvent`s then one `QueryResult` (`type: "result"`). `AgentEvent.payload` already carries `{"adapter": <name|null>}` before every LLM agent turn (`orchestrator.py:_adapter_ev`) — the wire data for the adapter badge already exists, it's just unread on the frontend.
- `GET /ws` — same event stream over WebSocket. **Currently unused by the frontend**; `queryClient.ts` uses the NDJSON fetch stream instead, which already works and needs no reconnect logic.
- `GET /session`, `GET /session/{id}`, `POST /session` — session list/get/create. No frontend consumer yet.
- `GET /db/profile` — returns the current `DBProfile` (404 until a query has run once). No frontend consumer yet.

**What this means for scope**: Steps 1, 4 (transport), 5 (progress rendering shell), 6 (free-text input), and half of Step 9 (didactic summary) are **substantially done**, just not in the target shape (no tokens, no Zustand, one HTML blob instead of four panels, no adapter badge, no WebSocket). The remaining work is real but is a *refactor + additive-components* pass, not a from-scratch build.

---

## Step Map (v1 Day 3 → v2 Day 2, realigned)

| Step | Content | Source | Current state | Delta |
|---|---|---|---|---|
| 1 | Install frontend dependencies (recharts, zustand) | v1 D3-S1 | **Not installed** | `npm install recharts zustand` in `frontend/` |
| 2 | `styles/tokens.css` — glass theme ported to design tokens + CSS Modules | v1 D3-S2 | `index.css` has the 5 themes as raw CSS custom properties, un-tokenized | Extract the shared token set (spacing, radii, font scale, z-index) into `styles/tokens.css`; keep the 5 theme palettes as `[data-theme]` blocks; migrate component-specific rules to `*.module.css` incrementally (don't rewrite `index.css` wholesale in one pass — theme switching must keep working throughout) |
| 3 | Zustand stores (query, session, dbProfile, progress) | v1 D3-S3 | **Not started** — all state is `useState` in `App.tsx` | Introduce stores; `progress` store's `AgentProgress` item gets `adapter?: string` (already on the wire via `payload.adapter`, just needs to be read out in `queryClient.ts`'s event parsing and carried into the store) |
| 4 | API + WebSocket services (`api.ts`, `ws.ts`) | v1 D3-S4 | `queryClient.ts` (fetch+NDJSON) works and is the proven transport; `/ws` exists on the backend but has no client | **Decision needed** (see Delta 0 below) — default recommendation: keep NDJSON as primary, don't build `ws.ts` unless a concrete need (e.g. live multi-agent view independent of the request lifecycle) shows up. Move `queryClient.ts` → `services/api.ts` for layout compliance either way |
| 5 | `ProgressIndicator` | v1 D3-S5 | `AgentProgress.tsx` exists, renders inline in the chat feed | Add the adapter badge (Delta 1). Consider whether it stays chat-inline (current, didactic-friendly) or becomes a standalone panel per the original name — inline has worked fine so far, no reason to force a split |
| 6 | `QueryBuilder` (keyword-guided) → **inline autocomplete** | v1 D3-S6 | `InputArea.tsx` is free-text only, no suggestions | **Resolved (Delta 3 below):** cut the separate builder; add DB-context-aware autocompletion to the existing free-text box |
| 7 | `Visualization` (Recharts auto-chart) | v1 D3-S7 | **Not started** — results render as a plain HTML `<table>` via `renderRowsTable()` in `queryClient.ts` | New component; chart-type selection heuristic off `QueryResult.rows` shape; keep the existing table as the fallback/complement, not a replacement |
| 8 | `SessionLibrary` | v1 D3-S8 | **Not started** — backend `GET /session*` is live and unconsumed | New component; list + reload via `POST /query` with `session_id` (the `sessionIdRef` continuity mechanism already in `App.tsx` supports this) |
| 9 | Didactic answer panel (What / SQL / Why / Results) | v1 D3-S9 | Partially done — `buildResultHTML()` already assembles teaching summary + SQL + results, but as one concatenated HTML string, not four addressable panels, and "What I understood" (`intent.plain_restatement`) isn't surfaced at all today (only `teaching_summary`, which covers Why) | Split into real components (`AnswerPanel` with 4 sub-sections); surface `intent.plain_restatement` as its own "What I understood" block; keep `sqlHighlighter`/`markdownRenderer` reuse |
| 10 | Rewrite `App.tsx` | v1 D3-S10 | `App.tsx` already reflects the pipeline (theme cycling, page toggle, `streamQuery` loop, session continuity) | Adapt in place as stores/components land — this is now an incremental migration, not a rewrite |
| 11 | Verify no Tailwind artifacts | v1 D3-S11 | Never introduced | `npm run build` + scan `dist/` — unchanged, trivial pass expected |

---

## v2 Delta 0 — Transport: Keep NDJSON, `/ws` Stays Unwired (New)

The original plan assumed a WebSocket-first frontend (`ws.ts` in Step 4, `ProgressIndicator` wired to `/ws`). What actually shipped during sandbox detachment uses `fetch()` + NDJSON streaming (`queryClient.streamQuery`) against `POST /query`, and it already delivers live per-agent progress with no reconnect/backpressure complexity. Recommendation: **keep it**. `/ws` remains live on the backend (useful later for a detached/multi-client progress view) but is not a Day 2 dependency. This also keeps cut-line #4 in `MASTERPLAN.md` (§10) trivially satisfied — there's nothing to fall back from.

## v2 Delta 1 — Adapter Badge in `AgentProgress`

The orchestrator already emits `payload.adapter` on the event immediately preceding each LLM agent's turn (`orchestrator.py:_adapter_ev`, confirmed for `query_understanding`, `clarification`, `sql_generator`, `verification`). The frontend `AgentEvent` type (`queryClient.ts`) already has `payload?: Record<string, unknown> | null`, but `AgentProgress.tsx`'s `collapse()` only reads `agent`, `status`, `message` — `payload.adapter` is parsed off the wire and then dropped.

Fix: thread `adapter` through `collapse()`'s `Step` shape and render a small badge — `profile: sql_generator` (or `base` when `adapter` is `null`, matching the fail-safe semantics in `llm_service.load_adapter`). This is deliberately didactic: the learner sees *which specialization* answered each stage, and Day 3's A/B harness reuses this same signal.

```typescript
interface Step {
  agent: AgentName;
  status: AgentEvent["status"];
  message: string;
  adapter?: string | null; // from payload.adapter — instruction profile active for this turn
}
```

If/when a `progress` Zustand store lands (Step 3), this field moves there; until then it can stay local to `AgentProgress.tsx`.

## v2 Delta 2 — `DBProfileForm` Reads, Not Writes (Yet)

`GET /db/profile` is live and returns the full `DBProfile` (schema graph, glossary, coded-value maps, source-of-truth, relationship edges) once a query has run at least once — confirmed in `backend/app/api/routes/db.py` and the shape in `backend/app/models/envelope.py`. Nothing on the frontend calls it yet. Render the **DBProfile card** as a read-only "map of the database". The editable survey (writing back user corrections) is deferred to Day 4, when a genuinely unknown database can first appear. Handle the pre-first-query 404 gracefully (e.g. hide the card, or show a "run a query to build the profile" placeholder) rather than treating it as an error state.

---

## v2 Delta 3 — `QueryBuilder` Resolved: Inline Autocomplete, Not a Second Input Mode

**Decision (2026-07-02):** the keyword-guided builder is cut as a separate UI. `InputArea.tsx` stays free-text (already proven against the Query Understanding agent — Day 1 Gate: 6/8 EC probes on free-text-style prompts) and gains **inline autocompletion**: as the learner types the last word of the sentence, a small dropdown suggests DB-context terms — e.g. typing *"I want to know the 5 most listened s…"* suggests **"songs"**. This is the easiest version of "lower the barrier": zero new input paradigm, one small addition to the existing box.

**Vocabulary — two sources, merged client-side, no new backend endpoint:**
1. `GET /db/profile` (already live) → table names, column names, and glossary abbreviation/meaning words. This is the literal schema vocabulary (`tracks`, `albums`, `trk_dur_ms`, …).
2. A short **static curated synonym list** shipped with the frontend component (plain constant, ~15–20 entries: `songs`, `tracks`, `artists`, `albums`, `playlists`, `plays`, `listens`, `streams`, `genres`, `singles`, `subscribers`, `users`, …). This is what makes "songs" suggestible even though the real table is `tracks` — the schema alone doesn't carry colloquial phrasing, and mining it out of the context markdown automatically is not the easiest path. A hand-picked list next to `InputArea.tsx` is enough and is trivial to extend as new edge cases surface.

**No backend changes required.** `_db_profile` is still built lazily on first query (`orchestrator.py`), so `GET /db/profile` 404s until then — the frontend just degrades gracefully: fetch on mount, and if 404, suggestions run on the static synonym list alone until the first `QueryResult` comes back (`App.tsx`'s existing `sendMessage` success path), at which point re-fetch `/db/profile` once to add the real schema terms. No polling, no eager-build change to Day 1's orchestrator.

**Matching:** pure client-side prefix filter (case-insensitive) over the merged vocabulary array (low hundreds of terms — no debounce or network call needed per keystroke). Split the input value on whitespace, match against the last (in-progress) token, show the top ~5 matches in a small dropdown anchored under `InputArea`.

**Interaction (revised 2026-07-02):**
- `Enter` or `Space` → **accept** the top suggestion (replaces the in-progress last word, keeps the rest of the sentence). Click on a dropdown entry accepts that specific one instead of the top match.
- `Backspace` or `Delete` → **cancel/discard** the suggestion dropdown (closes it; the keystroke still performs its normal edit on the text underneath).
- **While the dropdown is open, `Enter` is locked for chat submission** — it is fully consumed by the accept action, not the send action. `InputArea`'s submit-on-Enter handler must check "is a suggestion currently showing?" first; only when no dropdown is open does `Enter` send the message. This means accepting a suggestion always takes one extra `Enter`/click to then send, which is the point — it prevents an accidental send mid-word.
- Suggestions recompute on every keystroke from the (possibly shortened) in-progress last word; once the dropdown is dismissed (accepted or cancelled), `Enter` reverts to normal send behavior until a new partial word starts matching again.

---

## Gate D2 Verification

1. `python start.py` → open the app.
2. Type *"I want to know the 5 most listened s"* into the chat box and confirm "songs" appears in the autocomplete dropdown; accept it and send. Watch per-agent progress live in `AgentProgress`, with adapter badges reading a real profile name (or `base`) per LLM agent.
3. Answer view renders four distinct didactic panels — *What I understood*, *The SQL* (highlighted), *Why this query*, *Results + chart* — not one concatenated HTML blob.
4. Open `SessionLibrary`, reload a previous session (`sessionIdRef`-style continuity, now surfaced in UI).
5. Open the `DBProfile` card and confirm it matches `GET /db/profile`'s current content.
6. `npm run build` then scan `dist/` for `tailwind` — zero hits.

---

## File Checklist

| File | Action |
|---|---|
| `frontend/package.json` | Add `recharts`, `zustand` |
| `frontend/src/styles/tokens.css` | New — extracted from `index.css` |
| `frontend/src/stores/*.ts` | New — query, session, dbProfile, progress |
| `frontend/src/services/api.ts` | New — `queryClient.ts` relocated/renamed for layout compliance |
| `frontend/src/utils/queryClient.ts` | Superseded by `services/api.ts` (remove after migration, don't duplicate) |
| `frontend/src/components/AgentProgress.tsx` | Modified — adapter badge (Delta 1) |
| `frontend/src/components/AnswerPanel.tsx` (or similar) | New — splits `buildResultHTML()` into 4 addressable panels |
| `frontend/src/components/Visualization.tsx` | New — Recharts auto-chart |
| `frontend/src/components/SessionLibrary.tsx` | New — consumes `GET /session*` |
| `frontend/src/components/DBProfileForm.tsx` | New — read-only card, consumes `GET /db/profile` |
| `frontend/src/components/InputArea.tsx` | Modified — inline autocomplete dropdown (Delta 3), replaces the `QueryBuilder.tsx` step |
| `frontend/src/utils/autocompleteVocabulary.ts` (or similar) | New — static synonym list + merge/filter helpers against `DBProfile` |
| `frontend/src/App.tsx` | Modified in place as stores/components land |
| `frontend/src/index.css` | Reduced incrementally as rules move to `tokens.css` + CSS Modules |
