export const API_BASE = 'http://localhost:5000';

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

export interface SqlCandidate {
    sql: string;
    rationale?: string | null;
    generation_method?: string;
}

export interface LayerResult {
    passed: boolean;
    message: string;
}

export interface VerifyReport {
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

// ── session wire types (backend/app/api/routes/session.py) ─────────────────────

export interface SessionSummary {
    session_id: string;
    title: string;
    db_name: string;
    created_at: string;
    updated_at: string;
}

export interface SessionTurn {
    turn_id: string;
    session_id: string;
    created_at: string;
    role: 'user' | 'assistant';
    content: string;
    sql: string | null;
    /** JSON-encoded string of the first 10 result rows, or null. */
    rows_json: string | null;
}

export interface SessionDetail extends SessionSummary {
    turns: SessionTurn[];
}

// ── DB profile wire types (backend/app/models/envelope.py DBProfile) ───────────

export interface DBColumn {
    name: string;
    data_type: string;
    is_nullable: boolean;
    is_primary_key: boolean;
    is_foreign_key: boolean;
    references: string | null;
    cardinality: number | null;
    sample_values: unknown[];
    glossary_note: string | null;
}

export interface DBTable {
    name: string;
    row_count: number | null;
    columns: DBColumn[];
    description: string | null;
}

export interface DBProfile {
    db_name: string;
    domain_description: string | null;
    tables: DBTable[];
    relationship_edges: Array<[string, string]>;
    coded_value_maps: Record<string, Record<string, string>>;
    glossary: Record<string, string>;
    source_of_truth: Record<string, string>;
    sensitivity: Record<string, boolean>;
    created_at: string;
}

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
    const response = await fetch(`${API_BASE}/query`, {
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

// ── REST fetchers ───────────────────────────────────────────────────────────────

export async function fetchSessions(): Promise<SessionSummary[]> {
    const response = await fetch(`${API_BASE}/session`);
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
    const data = await response.json();
    return data.sessions as SessionSummary[];
}

export async function fetchSession(sessionId: string): Promise<SessionDetail> {
    const response = await fetch(`${API_BASE}/session/${encodeURIComponent(sessionId)}`);
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
    return (await response.json()) as SessionDetail;
}

/**
 * GET /db/profile. Returns null on 404 — the profile is built lazily on the
 * first query, so "not there yet" is an expected state, not an error.
 */
export async function fetchDbProfile(): Promise<DBProfile | null> {
    const response = await fetch(`${API_BASE}/db/profile`);
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
    return (await response.json()) as DBProfile;
}
