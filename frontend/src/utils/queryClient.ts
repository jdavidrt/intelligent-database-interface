import { highlightSQL } from './sqlHighlighter';
import { renderMarkdown } from './markdownRenderer';

const QUERY_URL = 'http://localhost:5000/query';

// ── wire types (mirror backend/app/models/envelope.py) ─────────────────────────

export type AgentName =
    | 'context_manager'
    | 'query_understanding'
    | 'clarification'
    | 'sql_generator'
    | 'verification'
    | 'visualization'
    | 'session_manager'
    | 'orchestrator';

export interface AgentEvent {
    type: 'event';
    event_id: string;
    session_id: string;
    agent: AgentName;
    status: 'started' | 'progress' | 'done' | 'error';
    message: string;
    payload?: Record<string, unknown> | null;
}

interface SqlCandidate {
    sql: string;
    rationale?: string | null;
    generation_method?: string;
}

interface LayerResult {
    passed: boolean;
    message: string;
}

interface VerifyReport {
    syntax: LayerResult;
    semantic: LayerResult;
    sanity: LayerResult;
    overall_passed: boolean;
    repaired_sql?: string | null;
    repair_explanation?: string | null;
}

export interface QueryResult {
    type: 'result';
    session_id: string;
    intent?: { plain_restatement?: string | null } | null;
    sql?: SqlCandidate | null;
    verify?: VerifyReport | null;
    rows: Array<Record<string, unknown>>;
    row_count: number;
    teaching_summary?: string | null;
    error?: string | null;
}

export type StreamItem = AgentEvent | QueryResult;

// ── streaming ──────────────────────────────────────────────────────────────────

/**
 * POST /query and yield each NDJSON line as a typed event. The final item is the
 * QueryResult (type='result'); everything before it is an AgentEvent.
 */
export async function* streamQuery(
    message: string,
    sessionId: string | null,
    signal: AbortSignal,
): AsyncGenerator<StreamItem> {
    const response = await fetch(QUERY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: sessionId }),
        signal,
    });

    if (!response.ok || !response.body) {
        throw new Error(`Backend returned HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let nl: number;
        while ((nl = buffer.indexOf('\n')) >= 0) {
            const line = buffer.slice(0, nl).trim();
            buffer = buffer.slice(nl + 1);
            const item = parseLine(line);
            if (item) yield item;
        }
    }

    const tail = buffer.trim();
    if (tail) {
        const item = parseLine(tail);
        if (item) yield item;
    }
}

function parseLine(line: string): StreamItem | null {
    if (!line) return null;
    try {
        const obj = JSON.parse(line);
        // The final result carries type='result'; agent events have no type field.
        if (obj.type === 'result') return obj as QueryResult;
        return { type: 'event', ...obj } as AgentEvent;
    } catch {
        return null;
    }
}

// ── final-result → bot message HTML ────────────────────────────────────────────

function escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** Render up to `limit` result rows as a compact HTML table. */
function renderRowsTable(rows: Array<Record<string, unknown>>, limit = 50): string {
    if (rows.length === 0) return '<p class="result-empty">Query ran successfully — 0 rows returned.</p>';

    const cols = Object.keys(rows[0]);
    const shown = rows.slice(0, limit);

    const head = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');
    const body = shown
        .map(row => {
            const cells = cols
                .map(c => {
                    const v = row[c];
                    const text = v === null || v === undefined ? '∅' : String(v);
                    return `<td>${escapeHtml(text)}</td>`;
                })
                .join('');
            return `<tr>${cells}</tr>`;
        })
        .join('');

    const more =
        rows.length > limit
            ? `<div class="result-more">… ${rows.length - limit} more row(s)</div>`
            : '';

    return (
        `<div class="result-table-wrap"><table class="result-table">` +
        `<thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>${more}`
    );
}

/** Build the bot-message HTML string for a completed /query result. */
export function buildResultHTML(result: QueryResult): string {
    let html = '';

    // 1. Teaching summary (markdown). Also covers the clarification branch,
    //    whose teaching_summary is the follow-up question.
    if (result.teaching_summary) {
        html += `<div class="section-body">${renderMarkdown(result.teaching_summary)}</div>`;
    }

    // 2. Generated SQL (syntax-highlighted).
    if (result.sql?.sql) {
        html += `<h3 class="section-heading">SQL Query</h3>`;
        html +=
            `<div class="section-body"><pre><code class="lang-sql">` +
            `${highlightSQL(result.sql.sql)}</code></pre></div>`;
    }

    // 3. Results — only when SQL was executed (no error, verified path).
    if (!result.error && result.sql?.sql) {
        html += `<h3 class="section-heading">Results</h3>`;
        html += `<div class="section-body">${renderRowsTable(result.rows)}</div>`;
    }

    // 4. Error (verification failure, execution error, etc.).
    if (result.error) {
        html += `<p class="result-error">⚠️ ${escapeHtml(result.error)}</p>`;
    }

    // Fallback so a message never renders empty.
    if (!html.trim()) {
        html = `<p>${escapeHtml('No response produced.')}</p>`;
    }

    return html;
}
