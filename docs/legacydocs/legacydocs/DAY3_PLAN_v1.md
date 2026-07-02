# Day 3 — Frontend Rebuild (No Tailwind) & Visualization
## IDI Implementation Plan

**Goal:** The didactic UI — a learner sees the reasoning, the schema, the chart, and the lesson.

**Gate D3:** A non-SQL user runs a query end-to-end in the browser, sees live per-agent progress, a rendered chart, and the plain-language "why". Manual check confirms no Tailwind artifacts in the bundle.

**Pre-condition:** Gate D2 passed — `/query` streams real agent events and returns rows.

**Key constraint (D1 scope lock):** No Tailwind, no shadcn/ui. CSS Modules + design tokens only. The existing `index.css` glass theme is the design reference — port its CSS variables into a dedicated `tokens.css` and convert component styles to `.module.css` files.

---

## Step 1 — Install Frontend Dependencies

In the `frontend/` directory:

```
cd frontend
npm install zustand recharts
npm install --save-dev @types/recharts
```

Verify `package.json` now lists `zustand` and `recharts` under `dependencies`.

---

## Step 2 — Create `styles/tokens.css`

The existing `index.css` already defines CSS custom properties (--body-bg, --card-bg, --primary, etc.) — these are the design tokens. Extract them into a standalone file so all CSS Modules can reference them.

Create `frontend/src/styles/tokens.css`:

```css
/*
 * IDI Design Tokens — glass theme + multi-palette variables.
 * Import this file once in main.tsx. All component CSS Modules
 * reference these variables via var(--token-name).
 */

/* Default palette: Mystic Dusk */
:root {
    --color-bg:            radial-gradient(circle at top left, #2d2b55, #22223b);
    --color-card:          rgba(74, 78, 105, 0.45);
    --color-primary:       #c9ada7;
    --color-primary-hover: #9a8c98;
    --color-text:          #f2e9e4;
    --color-text-dim:      #9a8c98;
    --color-border:        rgba(201, 173, 167, 0.25);
    --color-user-bubble:   #4a4e69;
    --color-bot-bubble:    rgba(34, 34, 59, 0.75);
    --color-header-grad:   linear-gradient(to right, #c9ada7, #f2e9e4);
    --color-input-bg:      rgba(255, 255, 255, 0.06);
    --color-input-focus:   rgba(255, 255, 255, 0.10);
    --color-code-bg:       rgba(0, 0, 0, 0.35);
    --color-code:          #c9ada7;
    --color-scrollbar:     rgba(201, 173, 167, 0.30);
    --color-success:       #6fcf97;
    --color-error:         #eb5757;
    --color-warning:       #f2994a;

    /* Typography */
    --font-sans: 'Inter', system-ui, sans-serif;
    --font-mono: 'Fira Mono', 'Consolas', monospace;
    --font-size-base: 1rem;
    --font-size-sm:   0.875rem;
    --font-size-xs:   0.75rem;

    /* Spacing */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-6: 24px;
    --space-8: 32px;

    /* Radius */
    --radius-sm: 6px;
    --radius-md: 12px;
    --radius-lg: 18px;

    /* Transitions */
    --transition-fast: 150ms ease;
    --transition-base: 250ms ease;

    /* Agent progress colors */
    --agent-context:     #7eb8f7;
    --agent-understand:  #a8dadc;
    --agent-clarify:     #f2cc8f;
    --agent-sql:         #81b29a;
    --agent-verify:      #e07a5f;
    --agent-visualize:   #b06ab3;
    --agent-orchestrate: #c9ada7;
}

/* Desert Bloom */
[data-theme="desert-bloom"] {
    --color-bg:            radial-gradient(circle at top right, #f2cc8f, #f4f1de);
    --color-card:          rgba(255, 255, 255, 0.78);
    --color-primary:       #e07a5f;
    --color-primary-hover: #c9674c;
    --color-text:          #3d405b;
    --color-text-dim:      #81b29a;
    --color-border:        rgba(61, 64, 91, 0.18);
    --color-user-bubble:   #e07a5f;
    --color-bot-bubble:    rgba(242, 204, 143, 0.45);
    --color-header-grad:   linear-gradient(to right, #e07a5f, #f2cc8f);
    --color-input-bg:      rgba(0, 0, 0, 0.04);
    --color-input-focus:   rgba(0, 0, 0, 0.07);
    --color-code-bg:       rgba(61, 64, 91, 0.07);
    --color-code:          #3d405b;
    --color-scrollbar:     rgba(224, 122, 95, 0.40);
}

/* Abyss */
[data-theme="abyss"] {
    --color-bg:            radial-gradient(ellipse at bottom, #4d194d, #1b3a4b 55%, #006466);
    --color-card:          rgba(11, 82, 91, 0.38);
    --color-primary:       #006466;
    --color-primary-hover: #0b525b;
    --color-text:          #d4f0f0;
    --color-text-dim:      #5fa8a8;
    --color-border:        rgba(0, 100, 102, 0.38);
    --color-user-bubble:   #065a60;
    --color-bot-bubble:    rgba(27, 58, 75, 0.85);
    --color-header-grad:   linear-gradient(to right, #5fe0e0, #b06ab3);
    --color-input-bg:      rgba(255, 255, 255, 0.05);
    --color-input-focus:   rgba(255, 255, 255, 0.09);
    --color-code-bg:       rgba(0, 0, 0, 0.42);
    --color-code:          #5fe0e0;
    --color-scrollbar:     rgba(0, 100, 102, 0.50);
}

/* Neon Burst */
[data-theme="neon-burst"] {
    --color-bg:            radial-gradient(circle at center, #4d2d8b, #3d348b 60%, #271d6a);
    --color-card:          rgba(61, 52, 139, 0.55);
    --color-primary:       #f7b801;
    --color-primary-hover: #f18701;
    --color-text:          #ffffff;
    --color-text-dim:      #b8a8ff;
    --color-border:        rgba(118, 120, 237, 0.38);
    --color-user-bubble:   #7678ed;
    --color-bot-bubble:    rgba(243, 91, 4, 0.13);
    --color-header-grad:   linear-gradient(to right, #f7b801, #f35b04);
    --color-input-bg:      rgba(255, 255, 255, 0.06);
    --color-input-focus:   rgba(255, 255, 255, 0.10);
    --color-code-bg:       rgba(0, 0, 0, 0.45);
    --color-code:          #f7b801;
    --color-scrollbar:     rgba(247, 184, 1, 0.35);
}

/* Lavender Dream */
[data-theme="lavender-dream"] {
    --color-bg:            radial-gradient(circle at top, #e0c3fc, #8ec5fc);
    --color-card:          rgba(255, 255, 255, 0.72);
    --color-primary:       #7b5ea7;
    --color-primary-hover: #6a4f8a;
    --color-text:          #2d2d44;
    --color-text-dim:      #7b5ea7;
    --color-border:        rgba(123, 94, 167, 0.22);
    --color-user-bubble:   #7b5ea7;
    --color-bot-bubble:    rgba(224, 195, 252, 0.55);
    --color-header-grad:   linear-gradient(to right, #7b5ea7, #8ec5fc);
    --color-input-bg:      rgba(0, 0, 0, 0.04);
    --color-input-focus:   rgba(0, 0, 0, 0.08);
    --color-code-bg:       rgba(123, 94, 167, 0.08);
    --color-code:          #7b5ea7;
    --color-scrollbar:     rgba(123, 94, 167, 0.35);
}
```

Update `frontend/src/main.tsx` to import tokens first:

```tsx
import './styles/tokens.css';
import './index.css';  // keep legacy styles for components not yet migrated
import { createRoot } from 'react-dom/client';
import App from './App';

createRoot(document.getElementById('root')!).render(<App />);
```

---

## Step 3 — Zustand Stores

Create `frontend/src/stores/queryStore.ts`:

```typescript
import { create } from 'zustand';

export interface AgentEventItem {
    agent: string;
    status: 'started' | 'progress' | 'done' | 'error';
    message: string;
    timestamp: string;
}

export interface QueryResult {
    session_id: string;
    intent?: { plain_restatement?: string; entities?: string[] };
    sql?: { sql: string; rationale?: string; generation_method?: string };
    verify?: {
        overall_passed: boolean;
        syntax: { passed: boolean; message: string };
        semantic: { passed: boolean; message: string };
        sanity: { passed: boolean; message: string };
        repaired_sql?: string;
    };
    rows: Record<string, unknown>[];
    row_count: number;
    teaching_summary?: string;
    error?: string;
}

interface QueryState {
    isRunning: boolean;
    events: AgentEventItem[];
    result: QueryResult | null;
    currentQuery: string;
    sessionId: string | null;

    setQuery: (q: string) => void;
    setSessionId: (id: string) => void;
    startRun: () => void;
    addEvent: (ev: AgentEventItem) => void;
    setResult: (r: QueryResult) => void;
    reset: () => void;
}

export const useQueryStore = create<QueryState>((set) => ({
    isRunning: false,
    events: [],
    result: null,
    currentQuery: '',
    sessionId: null,

    setQuery: (q) => set({ currentQuery: q }),
    setSessionId: (id) => set({ sessionId: id }),
    startRun: () => set({ isRunning: true, events: [], result: null }),
    addEvent: (ev) => set((s) => ({ events: [...s.events, ev] })),
    setResult: (r) => set({ result: r, isRunning: false }),
    reset: () => set({ isRunning: false, events: [], result: null, currentQuery: '' }),
}));
```

Create `frontend/src/stores/sessionStore.ts`:

```typescript
import { create } from 'zustand';

export interface SessionSummary {
    session_id: string;
    title: string;
    db_name: string;
    created_at: string;
    updated_at: string;
}

interface SessionState {
    sessions: SessionSummary[];
    activeSessionId: string | null;
    setSessions: (s: SessionSummary[]) => void;
    setActiveSession: (id: string | null) => void;
    addSession: (s: SessionSummary) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
    sessions: [],
    activeSessionId: null,
    setSessions: (s) => set({ sessions: s }),
    setActiveSession: (id) => set({ activeSessionId: id }),
    addSession: (s) => set((st) => ({ sessions: [s, ...st.sessions] })),
}));
```

Create `frontend/src/stores/dbProfileStore.ts`:

```typescript
import { create } from 'zustand';

export interface ColumnInfo {
    name: string;
    data_type: string;
    is_nullable: boolean;
    is_primary_key: boolean;
    is_foreign_key: boolean;
    references?: string;
}

export interface TableInfo {
    name: string;
    row_count?: number;
    columns: ColumnInfo[];
}

export interface DBProfile {
    db_name: string;
    domain_description?: string;
    tables: TableInfo[];
    glossary: Record<string, string>;
    coded_value_maps: Record<string, Record<string, string>>;
}

interface DBProfileState {
    profile: DBProfile | null;
    isLoading: boolean;
    setProfile: (p: DBProfile) => void;
    setLoading: (v: boolean) => void;
}

export const useDBProfileStore = create<DBProfileState>((set) => ({
    profile: null,
    isLoading: false,
    setProfile: (p) => set({ profile: p, isLoading: false }),
    setLoading: (v) => set({ isLoading: v }),
}));
```

Create `frontend/src/stores/progressStore.ts`:

```typescript
import { create } from 'zustand';

export type AgentName =
    | 'context_manager' | 'query_understanding' | 'clarification'
    | 'sql_generator' | 'verification' | 'visualization'
    | 'session_manager' | 'orchestrator';

export interface AgentStep {
    agent: AgentName;
    status: 'idle' | 'running' | 'done' | 'error';
    message: string;
}

const PIPELINE_ORDER: AgentName[] = [
    'context_manager', 'query_understanding', 'clarification',
    'sql_generator', 'verification', 'orchestrator',
];

const makeIdle = (): Record<AgentName, AgentStep> =>
    Object.fromEntries(
        PIPELINE_ORDER.map((a) => [a, { agent: a, status: 'idle', message: '' }])
    ) as Record<AgentName, AgentStep>;

interface ProgressState {
    steps: Record<AgentName, AgentStep>;
    order: AgentName[];
    updateStep: (agent: AgentName, status: AgentStep['status'], message: string) => void;
    reset: () => void;
}

export const useProgressStore = create<ProgressState>((set) => ({
    steps: makeIdle(),
    order: PIPELINE_ORDER,
    updateStep: (agent, status, message) =>
        set((s) => ({ steps: { ...s.steps, [agent]: { agent, status, message } } })),
    reset: () => set({ steps: makeIdle() }),
}));
```

---

## Step 4 — API & WebSocket Services

Create `frontend/src/services/api.ts`:

```typescript
const BASE = 'http://localhost:5000';

export async function fetchDBProfile() {
    const r = await fetch(`${BASE}/db/profile`);
    if (!r.ok) throw new Error('DBProfile not available');
    return r.json();
}

export async function fetchSessions() {
    const r = await fetch(`${BASE}/session`);
    if (!r.ok) throw new Error('Could not load sessions');
    return r.json();
}

export async function fetchSession(id: string) {
    const r = await fetch(`${BASE}/session/${id}`);
    if (!r.ok) throw new Error('Session not found');
    return r.json();
}

/**
 * POST /query and consume the NDJSON stream.
 * Calls onEvent for each AgentEvent line, onResult for the final result line.
 */
export async function runQuery(
    message: string,
    sessionId: string | null,
    onEvent: (ev: Record<string, unknown>) => void,
    onResult: (r: Record<string, unknown>) => void,
    signal?: AbortSignal,
): Promise<void> {
    const resp = await fetch(`${BASE}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal,
    });

    if (!resp.body) throw new Error('No response body');

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
            if (!line.trim()) continue;
            try {
                const data = JSON.parse(line);
                if (data.type === 'result') {
                    onResult(data);
                } else {
                    onEvent(data);
                }
            } catch {
                // ignore malformed lines
            }
        }
    }
}
```

Create `frontend/src/services/ws.ts`:

```typescript
/**
 * WebSocket client for /ws — alternative to NDJSON streaming.
 * Used by ProgressIndicator when connecting via WS directly.
 */
export class IDIWebSocket {
    private ws: WebSocket | null = null;
    private readonly url = 'ws://localhost:5000/ws';

    connect(
        onEvent: (data: Record<string, unknown>) => void,
        onResult: (data: Record<string, unknown>) => void,
        onClose?: () => void,
    ) {
        this.ws = new WebSocket(this.url);
        this.ws.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.type === 'result') {
                    onResult(data);
                } else {
                    onEvent(data);
                }
            } catch {
                // ignore
            }
        };
        this.ws.onclose = onClose ?? (() => {});
    }

    send(message: string, sessionId: string | null) {
        this.ws?.send(JSON.stringify({ message, session_id: sessionId }));
    }

    disconnect() {
        this.ws?.close();
        this.ws = null;
    }
}
```

---

## Step 5 — `ProgressIndicator` Component

Create `frontend/src/components/ProgressIndicator/ProgressIndicator.module.css`:

```css
.root {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    backdrop-filter: blur(10px);
}

.step {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--font-size-sm);
    color: var(--color-text-dim);
    transition: color var(--transition-fast);
}

.step.running { color: var(--color-text); }
.step.done    { color: var(--color-success); }
.step.error   { color: var(--color-error); }

.dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-border);
    flex-shrink: 0;
    transition: background var(--transition-fast);
}

.step.running .dot { background: var(--color-primary); animation: pulse 1s infinite; }
.step.done    .dot { background: var(--color-success); }
.step.error   .dot { background: var(--color-error); }

.label { flex: 1; }
.message { font-size: var(--font-size-xs); color: var(--color-text-dim); opacity: 0.8; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}
```

Create `frontend/src/components/ProgressIndicator/ProgressIndicator.tsx`:

```tsx
import styles from './ProgressIndicator.module.css';
import { useProgressStore, AgentName } from '../../stores/progressStore';

const LABELS: Record<AgentName, string> = {
    context_manager:   'Context Manager',
    query_understanding: 'Query Understanding',
    clarification:     'Clarification',
    sql_generator:     'SQL Generator',
    verification:      'Verification',
    visualization:     'Visualization',
    session_manager:   'Session Manager',
    orchestrator:      'Orchestrator',
};

export function ProgressIndicator() {
    const { steps, order } = useProgressStore();

    const visible = order.filter((a) => steps[a].status !== 'idle');
    if (visible.length === 0) return null;

    return (
        <div className={styles.root} role="status" aria-label="Pipeline progress">
            {visible.map((agent) => {
                const step = steps[agent];
                return (
                    <div key={agent} className={`${styles.step} ${styles[step.status]}`}>
                        <span className={styles.dot} />
                        <span className={styles.label}>{LABELS[agent]}</span>
                        {step.message && (
                            <span className={styles.message}>{step.message}</span>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
```

---

## Step 6 — `QueryBuilder` Component

Create `frontend/src/components/QueryBuilder/QueryBuilder.module.css`:

```css
.root {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-4);
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    backdrop-filter: blur(12px);
}

.textarea {
    width: 100%;
    min-height: 80px;
    background: var(--color-input-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text);
    font-family: var(--font-sans);
    font-size: var(--font-size-base);
    padding: var(--space-3);
    resize: none;
    outline: none;
    transition: border-color var(--transition-fast), background var(--transition-fast);
    box-sizing: border-box;
}

.textarea:focus {
    border-color: var(--color-primary);
    background: var(--color-input-focus);
}

.row { display: flex; gap: var(--space-2); align-items: center; flex-wrap: wrap; }

.btn {
    padding: var(--space-2) var(--space-4);
    border: none;
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: var(--font-size-sm);
    font-weight: 600;
    cursor: pointer;
    transition: background var(--transition-fast), opacity var(--transition-fast);
}

.btnPrimary {
    background: var(--color-primary);
    color: #fff;
}
.btnPrimary:hover  { background: var(--color-primary-hover); }
.btnPrimary:disabled { opacity: 0.5; cursor: not-allowed; }

.btnSecondary {
    background: transparent;
    color: var(--color-primary);
    border: 1px solid var(--color-primary);
}
.btnSecondary:hover { background: var(--color-input-bg); }

.suggestion {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    cursor: pointer;
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-sm);
    border: 1px solid var(--color-border);
    background: transparent;
    transition: background var(--transition-fast);
}
.suggestion:hover { background: var(--color-input-bg); }
```

Create `frontend/src/components/QueryBuilder/QueryBuilder.tsx`:

```tsx
import { useState, useRef, KeyboardEvent } from 'react';
import styles from './QueryBuilder.module.css';

const SUGGESTIONS = [
    'How many tracks are standalone singles?',
    'Show me all artists from Colombia.',
    'Which subscription plans include high-fidelity audio?',
    'Which genres have subgenres?',
    'What is the average track duration in minutes?',
];

interface QueryBuilderProps {
    onSubmit: (query: string) => void;
    onStop: () => void;
    isRunning: boolean;
}

export function QueryBuilder({ onSubmit, onStop, isRunning }: QueryBuilderProps) {
    const [text, setText] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const submit = () => {
        const q = text.trim();
        if (q && !isRunning) {
            onSubmit(q);
            setText('');
        }
    };

    const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submit();
        }
    };

    return (
        <div className={styles.root}>
            <div className={styles.row}>
                {SUGGESTIONS.map((s) => (
                    <button
                        key={s}
                        className={styles.suggestion}
                        onClick={() => setText(s)}
                        disabled={isRunning}
                        type="button"
                    >
                        {s.length > 40 ? s.slice(0, 38) + '…' : s}
                    </button>
                ))}
            </div>

            <textarea
                ref={textareaRef}
                className={styles.textarea}
                placeholder="Ask anything about the database…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKey}
                disabled={isRunning}
                rows={3}
            />

            <div className={styles.row}>
                <button
                    className={`${styles.btn} ${styles.btnPrimary}`}
                    onClick={submit}
                    disabled={isRunning || !text.trim()}
                    type="button"
                >
                    {isRunning ? 'Running…' : 'Ask IDI'}
                </button>
                {isRunning && (
                    <button
                        className={`${styles.btn} ${styles.btnSecondary}`}
                        onClick={onStop}
                        type="button"
                    >
                        Stop
                    </button>
                )}
            </div>
        </div>
    );
}
```

---

## Step 7 — `Visualization` Component (Recharts Auto-Chart)

Create `frontend/src/components/Visualization/chartSelector.ts`:

```typescript
/**
 * Select the best Recharts chart type for a given result set.
 * Returns a chart spec the Visualization component renders.
 */

export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'none';

export interface ChartSpec {
    type: ChartType;
    xKey: string;
    yKey: string;
    reason: string;
}

export function selectChart(
    rows: Record<string, unknown>[],
    sql?: string,
): ChartSpec {
    if (!rows || rows.length === 0) return { type: 'none', xKey: '', yKey: '', reason: 'No rows' };

    const keys = Object.keys(rows[0]);
    if (keys.length < 2) return { type: 'none', xKey: '', yKey: '', reason: 'Single column result' };

    // Find numeric columns
    const numericKeys = keys.filter((k) =>
        rows.every((r) => r[k] === null || !isNaN(Number(r[k])))
    );
    const textKeys = keys.filter((k) => !numericKeys.includes(k));

    const xKey = textKeys[0] ?? keys[0];
    const yKey = numericKeys[0] ?? keys[1];

    // Heuristic: ≤ 8 categories → pie; time series keyword → line; else bar
    const sqlUpper = (sql ?? '').toUpperCase();
    const isTimeSeries =
        /DATE|MONTH|YEAR|WEEK|DAY/.test(sqlUpper) ||
        /date|month|year|week|day/.test(xKey.toLowerCase());
    const isCount = rows.length <= 8 && textKeys.length > 0;

    if (isTimeSeries) {
        return { type: 'line', xKey, yKey, reason: 'Time-series detected in SQL or column name' };
    }
    if (isCount && rows.length <= 6) {
        return { type: 'pie', xKey, yKey, reason: 'Small category set — pie chart' };
    }
    return { type: 'bar', xKey, yKey, reason: 'Default: bar chart for categorical comparison' };
}
```

Create `frontend/src/components/Visualization/Visualization.module.css`:

```css
.root {
    padding: var(--space-4);
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    backdrop-filter: blur(10px);
}

.title {
    font-size: var(--font-size-sm);
    font-weight: 600;
    color: var(--color-text-dim);
    margin-bottom: var(--space-3);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.reason {
    font-size: var(--font-size-xs);
    color: var(--color-text-dim);
    margin-top: var(--space-2);
    font-style: italic;
}

.noChart { color: var(--color-text-dim); font-size: var(--font-size-sm); }
```

Create `frontend/src/components/Visualization/Visualization.tsx`:

```tsx
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { selectChart } from './chartSelector';
import styles from './Visualization.module.css';

interface VisualizationProps {
    rows: Record<string, unknown>[];
    sql?: string;
}

const PALETTE = ['#c9ada7', '#7eb8f7', '#81b29a', '#f2cc8f', '#b06ab3', '#e07a5f'];

export function Visualization({ rows, sql }: VisualizationProps) {
    const spec = selectChart(rows, sql);

    if (spec.type === 'none') {
        return (
            <div className={styles.root}>
                <div className={styles.noChart}>{spec.reason}</div>
            </div>
        );
    }

    const data = rows.map((r) => ({
        ...Object.fromEntries(
            Object.entries(r).map(([k, v]) => [k, v === null ? 0 : v])
        ),
    }));

    return (
        <div className={styles.root}>
            <div className={styles.title}>Chart — {spec.type}</div>
            <ResponsiveContainer width="100%" height={260}>
                {spec.type === 'bar' ? (
                    <BarChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                        <XAxis dataKey={spec.xKey} tick={{ fill: 'var(--color-text-dim)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--color-text-dim)', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)' }} />
                        <Bar dataKey={spec.yKey} fill={PALETTE[0]} radius={[4, 4, 0, 0]} />
                    </BarChart>
                ) : spec.type === 'line' ? (
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                        <XAxis dataKey={spec.xKey} tick={{ fill: 'var(--color-text-dim)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--color-text-dim)', fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)' }} />
                        <Line type="monotone" dataKey={spec.yKey} stroke={PALETTE[0]} strokeWidth={2} dot={false} />
                    </LineChart>
                ) : (
                    <PieChart>
                        <Pie data={data} dataKey={spec.yKey} nameKey={spec.xKey} cx="50%" cy="50%" outerRadius={100} label>
                            {data.map((_, i) => (
                                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                            ))}
                        </Pie>
                        <Legend />
                        <Tooltip />
                    </PieChart>
                )}
            </ResponsiveContainer>
            <div className={styles.reason}>{spec.reason}</div>
        </div>
    );
}
```

---

## Step 8 — `SessionLibrary` Component

Create `frontend/src/components/SessionLibrary/SessionLibrary.module.css`:

```css
.root {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    max-height: 400px;
    overflow-y: auto;
}

.item {
    padding: var(--space-3);
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: border-color var(--transition-fast);
}

.item:hover { border-color: var(--color-primary); }
.item.active { border-color: var(--color-primary); background: var(--color-input-focus); }

.title { font-weight: 600; color: var(--color-text); font-size: var(--font-size-sm); }
.meta  { font-size: var(--font-size-xs); color: var(--color-text-dim); margin-top: 2px; }
```

Create `frontend/src/components/SessionLibrary/SessionLibrary.tsx`:

```tsx
import { useEffect } from 'react';
import styles from './SessionLibrary.module.css';
import { useSessionStore } from '../../stores/sessionStore';
import { fetchSessions } from '../../services/api';

interface SessionLibraryProps {
    onSelect: (sessionId: string) => void;
}

export function SessionLibrary({ onSelect }: SessionLibraryProps) {
    const { sessions, activeSessionId, setSessions, setActiveSession } = useSessionStore();

    useEffect(() => {
        fetchSessions()
            .then((r) => setSessions(r.sessions ?? []))
            .catch(() => {});
    }, [setSessions]);

    if (sessions.length === 0) {
        return <div className={styles.root} style={{ color: 'var(--color-text-dim)', fontSize: 'var(--font-size-sm)' }}>No sessions yet.</div>;
    }

    return (
        <div className={styles.root}>
            {sessions.map((s) => (
                <div
                    key={s.session_id}
                    className={`${styles.item} ${s.session_id === activeSessionId ? styles.active : ''}`}
                    onClick={() => {
                        setActiveSession(s.session_id);
                        onSelect(s.session_id);
                    }}
                    role="button"
                    tabIndex={0}
                >
                    <div className={styles.title}>{s.title}</div>
                    <div className={styles.meta}>{s.db_name} · {s.updated_at.slice(0, 10)}</div>
                </div>
            ))}
        </div>
    );
}
```

---

## Step 9 — Didactic Answer Panel

Create `frontend/src/components/DidacticAnswer/DidacticAnswer.module.css`:

```css
.root {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
}

.panel {
    background: var(--color-card);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    backdrop-filter: blur(10px);
}

.panelHeader {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--color-border);
    font-size: var(--font-size-xs);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--color-text-dim);
}

.dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-primary);
}

.panelBody { padding: var(--space-4); }

/* Understanding panel */
.restatement {
    font-size: var(--font-size-base);
    color: var(--color-text);
    line-height: 1.6;
}

.entities {
    display: flex;
    gap: var(--space-1);
    flex-wrap: wrap;
    margin-top: var(--space-2);
}

.tag {
    font-size: var(--font-size-xs);
    padding: 2px var(--space-2);
    background: var(--color-input-bg);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    color: var(--color-text-dim);
    font-family: var(--font-mono);
}

/* SQL panel */
.sqlBlock {
    background: var(--color-code-bg);
    border-radius: var(--radius-sm);
    padding: var(--space-3);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    line-height: 1.6;
    overflow-x: auto;
    color: var(--color-code);
}

/* CSS classes injected by sqlHighlighter */
.sqlBlock :global(.sql-kw)      { color: #7eb8f7; font-weight: 700; }
.sqlBlock :global(.sql-string)  { color: #81b29a; }
.sqlBlock :global(.sql-number)  { color: #f2cc8f; }
.sqlBlock :global(.sql-comment) { color: var(--color-text-dim); font-style: italic; }
.sqlBlock :global(.sql-param)   { color: #b06ab3; }
.sqlBlock :global(.sql-op)      { color: var(--color-primary); }

.verifyRow {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
    margin-top: var(--space-3);
}

.verifyBadge {
    font-size: var(--font-size-xs);
    padding: 2px var(--space-2);
    border-radius: 4px;
    font-weight: 600;
}
.verifyPass { background: rgba(111,207,151,0.15); color: var(--color-success); }
.verifyFail { background: rgba(235,87,87,0.15);   color: var(--color-error); }

/* Why / rationale */
.rationale {
    font-size: var(--font-size-sm);
    color: var(--color-text);
    line-height: 1.7;
    white-space: pre-wrap;
}

/* Results table */
.tableWrap {
    overflow-x: auto;
    max-height: 320px;
    overflow-y: auto;
}

table { border-collapse: collapse; width: 100%; font-size: var(--font-size-sm); }
th {
    background: var(--color-input-bg);
    color: var(--color-text-dim);
    padding: var(--space-2) var(--space-3);
    text-align: left;
    border-bottom: 1px solid var(--color-border);
    font-weight: 600;
    white-space: nowrap;
}
td {
    padding: var(--space-2) var(--space-3);
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text);
}
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--color-input-bg); }

.rowCount { font-size: var(--font-size-xs); color: var(--color-text-dim); margin-top: var(--space-2); }
.error    { color: var(--color-error); font-size: var(--font-size-sm); padding: var(--space-3); }
```

Create `frontend/src/components/DidacticAnswer/DidacticAnswer.tsx`:

```tsx
import styles from './DidacticAnswer.module.css';
import { highlightSQL } from '../../utils/sqlHighlighter';
import { Visualization } from '../Visualization/Visualization';
import type { QueryResult } from '../../stores/queryStore';

interface DidacticAnswerProps {
    result: QueryResult;
}

export function DidacticAnswer({ result }: DidacticAnswerProps) {
    if (result.error) {
        return <div className={styles.error}>Error: {result.error}</div>;
    }

    const columns = result.rows.length > 0 ? Object.keys(result.rows[0]) : [];
    const verify = result.verify;
    const intent = result.intent;
    const sql = result.sql;

    return (
        <div className={styles.root}>

            {/* Panel 1: What I Understood */}
            <div className={styles.panel}>
                <div className={styles.panelHeader}>
                    <span className={styles.dot} />
                    What I Understood
                </div>
                <div className={styles.panelBody}>
                    <p className={styles.restatement}>
                        {intent?.plain_restatement ?? 'Query processed.'}
                    </p>
                    {intent?.entities && intent.entities.length > 0 && (
                        <div className={styles.entities}>
                            {intent.entities.map((e) => (
                                <span key={e} className={styles.tag}>{e}</span>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Panel 2: SQL */}
            {sql && (
                <div className={styles.panel}>
                    <div className={styles.panelHeader}>
                        <span className={styles.dot} style={{ background: 'var(--agent-sql)' }} />
                        SQL Query
                    </div>
                    <div className={styles.panelBody}>
                        <div
                            className={styles.sqlBlock}
                            dangerouslySetInnerHTML={{ __html: highlightSQL(sql.sql) }}
                        />
                        {verify && (
                            <div className={styles.verifyRow}>
                                {(['syntax', 'semantic', 'sanity'] as const).map((layer) => (
                                    <span
                                        key={layer}
                                        className={`${styles.verifyBadge} ${verify[layer].passed ? styles.verifyPass : styles.verifyFail}`}
                                    >
                                        {layer}: {verify[layer].message}
                                    </span>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Panel 3: Why This Query */}
            {sql?.rationale && (
                <div className={styles.panel}>
                    <div className={styles.panelHeader}>
                        <span className={styles.dot} style={{ background: 'var(--agent-verify)' }} />
                        Why This Query
                    </div>
                    <div className={styles.panelBody}>
                        <p className={styles.rationale}>{sql.rationale}</p>
                    </div>
                </div>
            )}

            {/* Panel 4: Results + Chart */}
            {result.rows.length > 0 && (
                <div className={styles.panel}>
                    <div className={styles.panelHeader}>
                        <span className={styles.dot} style={{ background: 'var(--agent-visualize)' }} />
                        Results
                    </div>
                    <div className={styles.panelBody}>
                        <Visualization rows={result.rows} sql={sql?.sql} />
                        <div className={styles.tableWrap}>
                            <table>
                                <thead>
                                    <tr>{columns.map((c) => <th key={c}>{c}</th>)}</tr>
                                </thead>
                                <tbody>
                                    {result.rows.slice(0, 100).map((row, i) => (
                                        <tr key={i}>
                                            {columns.map((c) => (
                                                <td key={c}>{String(row[c] ?? '')}</td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <div className={styles.rowCount}>{result.row_count} row(s) returned</div>
                    </div>
                </div>
            )}
        </div>
    );
}
```

---

## Step 10 — Rewrite `App.tsx`

Replace the current `App.tsx` entirely. The new version uses the new components, connects to `/query` NDJSON stream, and provides the full didactic layout:

```tsx
import { useCallback, useRef, useState } from 'react';
import { QueryBuilder } from './components/QueryBuilder/QueryBuilder';
import { ProgressIndicator } from './components/ProgressIndicator/ProgressIndicator';
import { DidacticAnswer } from './components/DidacticAnswer/DidacticAnswer';
import { SessionLibrary } from './components/SessionLibrary/SessionLibrary';
import { Header } from './components/Header';
import { useQueryStore } from './stores/queryStore';
import { useProgressStore } from './stores/progressStore';
import { useSessionStore } from './stores/sessionStore';
import { runQuery } from './services/api';
import type { AgentName } from './stores/progressStore';

const THEMES = [
    { name: 'Mystic Dusk', key: 'mystic-dusk' },
    { name: 'Desert Bloom', key: 'desert-bloom' },
    { name: 'Abyss', key: 'abyss' },
    { name: 'Neon Burst', key: 'neon-burst' },
    { name: 'Lavender Dream', key: 'lavender-dream' },
] as const;

export default function App() {
    const [themeIndex, setThemeIndex] = useState(0);
    const [showSessions, setShowSessions] = useState(false);

    const { isRunning, result, startRun, addEvent, setResult, currentQuery, setQuery, sessionId, setSessionId } = useQueryStore();
    const { updateStep, reset: resetProgress } = useProgressStore();
    const { setActiveSession } = useSessionStore();
    const abortRef = useRef<AbortController | null>(null);

    const cycleTheme = useCallback(() => {
        setThemeIndex((i) => {
            const next = (i + 1) % THEMES.length;
            const theme = THEMES[next];
            if (theme.key === 'mystic-dusk') {
                document.documentElement.removeAttribute('data-theme');
            } else {
                document.documentElement.setAttribute('data-theme', theme.key);
            }
            return next;
        });
    }, []);

    const handleSubmit = useCallback(async (query: string) => {
        setQuery(query);
        startRun();
        resetProgress();
        abortRef.current = new AbortController();

        try {
            await runQuery(
                query,
                sessionId,
                (ev) => {
                    const agent = ev.agent as AgentName;
                    const status = ev.status as 'started' | 'progress' | 'done' | 'error';
                    const message = (ev.message as string) ?? '';

                    addEvent({ agent, status, message, timestamp: new Date().toISOString() });
                    updateStep(
                        agent,
                        status === 'started' || status === 'progress' ? 'running'
                            : status === 'done' ? 'done' : 'error',
                        message,
                    );
                },
                (res) => {
                    setResult(res as any);
                    // Persist session reference
                    const sid = (res as any).session_id as string | undefined;
                    if (sid) setSessionId(sid);
                },
                abortRef.current.signal,
            );
        } catch (err) {
            if (err instanceof Error && err.name !== 'AbortError') {
                setResult({ session_id: sessionId ?? '', rows: [], row_count: 0, error: String(err) });
            }
        }
    }, [sessionId, startRun, resetProgress, addEvent, updateStep, setResult, setQuery, setSessionId]);

    const handleStop = useCallback(() => {
        abortRef.current?.abort();
    }, []);

    return (
        <div className="container">
            <Header
                themeName={THEMES[themeIndex].name}
                onThemeCycle={cycleTheme}
                page="chat"
                onPageChange={() => setShowSessions((v) => !v)}
            />

            <div style={{ display: 'grid', gridTemplateColumns: showSessions ? '280px 1fr' : '1fr', gap: '16px', padding: '0 16px 16px', flex: 1, overflowY: 'auto' }}>
                {showSessions && (
                    <aside>
                        <SessionLibrary
                            onSelect={(id) => {
                                setActiveSession(id);
                                setSessionId(id);
                            }}
                        />
                    </aside>
                )}

                <main style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    <QueryBuilder
                        onSubmit={handleSubmit}
                        onStop={handleStop}
                        isRunning={isRunning}
                    />

                    {(isRunning || result) && <ProgressIndicator />}

                    {result && <DidacticAnswer result={result} />}
                </main>
            </div>
        </div>
    );
}
```

---

## Step 11 — Verify No Tailwind Artifacts

After `npm run build` (from `frontend/`):

```
npm run build
# Check the dist/ output for any Tailwind class references:
findstr /s /i "tailwind" dist\*
# Expected: no matches

# Also verify no tw- or rounded- utility classes leaked in:
findstr /s /i "tw-\|bg-\|text-\|p-[0-9]\|m-[0-9]" dist\assets\*.js
# Expected: no matches (or only legitimate strings unrelated to Tailwind)
```

---

## Gate D3 Verification

1. `python start.py` — bring up the full stack.
2. Open `http://localhost:5173` in a browser.
3. Click a suggestion button (e.g. "How many tracks are standalone singles?") and press **Ask IDI**.
4. **Check:** ProgressIndicator shows live per-agent steps (context_manager → sql_generator → verification → orchestrator) animating in sequence.
5. **Check:** DidacticAnswer renders all four panels — "What I Understood", "SQL Query" (with syntax highlighting), "Why This Query" (rationale), "Results" (table + chart).
6. **Check:** Recharts bar/pie chart appears below the table.
7. **Check:** SessionLibrary panel opens when the nav toggle is clicked; sessions from Day 2 are listed.
8. Run `npm run build` and confirm zero Tailwind artifacts.

---

## File Checklist

| File | Action |
|---|---|
| `frontend/package.json` | zustand, recharts added |
| `frontend/src/styles/tokens.css` | Created |
| `frontend/src/main.tsx` | tokens.css imported |
| `frontend/src/stores/queryStore.ts` | Created |
| `frontend/src/stores/sessionStore.ts` | Created |
| `frontend/src/stores/dbProfileStore.ts` | Created |
| `frontend/src/stores/progressStore.ts` | Created |
| `frontend/src/services/api.ts` | Created |
| `frontend/src/services/ws.ts` | Created |
| `frontend/src/components/ProgressIndicator/ProgressIndicator.tsx` | Created |
| `frontend/src/components/ProgressIndicator/ProgressIndicator.module.css` | Created |
| `frontend/src/components/QueryBuilder/QueryBuilder.tsx` | Created |
| `frontend/src/components/QueryBuilder/QueryBuilder.module.css` | Created |
| `frontend/src/components/Visualization/chartSelector.ts` | Created |
| `frontend/src/components/Visualization/Visualization.tsx` | Created |
| `frontend/src/components/Visualization/Visualization.module.css` | Created |
| `frontend/src/components/SessionLibrary/SessionLibrary.tsx` | Created |
| `frontend/src/components/SessionLibrary/SessionLibrary.module.css` | Created |
| `frontend/src/components/DidacticAnswer/DidacticAnswer.tsx` | Created |
| `frontend/src/components/DidacticAnswer/DidacticAnswer.module.css` | Created |
| `frontend/src/App.tsx` | Rewritten |
