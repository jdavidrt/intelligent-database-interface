import { create } from 'zustand';
import { QueryResult, SessionDetail, streamQuery } from '../services/api';
import { useProgressStore } from './progressStore';
import { useSessionStore } from './sessionStore';
import { useDbProfileStore } from './dbProfileStore';

export interface Metrics {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
    timeMs: number;
}

export interface Message {
    id: string;
    role: 'user' | 'bot';
    /** For user: plain text. For bot: HTML fallback used when no `result` is present. */
    content: string;
    /** Structured pipeline result — rendered as the didactic AnswerPanel. */
    result?: QueryResult;
    /** Reconstructed from stored session turns (lossy: no intent/verify, first 10 rows only). */
    restored?: boolean;
    metrics?: Metrics;
}

const INITIAL_MESSAGE: Message = {
    id: 'init',
    role: 'bot',
    content: '<p>Hello! How can I help you today?</p>',
};

// Non-reactive request handle — lives outside the store state on purpose.
let abortController: AbortController | null = null;

// Bumped by newChat() so an aborted in-flight send() can't push stale
// bubbles (e.g. "Request cancelled") into the freshly reset feed.
let chatEpoch = 0;

function safeParseRows(json: string | null): Array<Record<string, unknown>> {
    if (!json) return [];
    try {
        const parsed = JSON.parse(json);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

interface QueryState {
    messages: Message[];
    /** True while a /query stream is in flight. */
    isWaiting: boolean;
    send: (text: string) => Promise<void>;
    stop: () => void;
    /** Reset the chat feed and detach from the active session (no page reload needed). */
    newChat: () => void;
    /** Replace the chat feed with a previously stored session's turns. */
    loadFromSession: (detail: SessionDetail) => void;
}

export const useQueryStore = create<QueryState>(set => ({
    messages: [INITIAL_MESSAGE],
    isWaiting: false,

    send: async text => {
        const epoch = chatEpoch;
        const pushBot = (msg: Omit<Message, 'id' | 'role'>) => {
            if (epoch !== chatEpoch) return; // chat was reset mid-flight
            set(state => ({
                messages: [
                    ...state.messages,
                    { id: crypto.randomUUID(), role: 'bot' as const, ...msg },
                ],
            }));
        };

        set(state => ({
            messages: [
                ...state.messages,
                { id: crypto.randomUUID(), role: 'user' as const, content: text },
            ],
            isWaiting: true,
        }));
        useProgressStore.getState().reset();
        abortController = new AbortController();

        try {
            let finalResult: QueryResult | null = null;
            for await (const item of streamQuery(
                text,
                useSessionStore.getState().activeSessionId,
                abortController.signal,
            )) {
                if (item.type === 'event') {
                    useProgressStore.getState().addEvent(item);
                } else {
                    finalResult = item;
                }
            }

            if (finalResult && epoch === chatEpoch) {
                useSessionStore.getState().setActiveSession(finalResult.session_id);
                pushBot({ content: '', result: finalResult });
                // The first query also builds the backend DBProfile — fetch it
                // once so autocomplete and the profile card gain real schema terms.
                if (!useDbProfileStore.getState().profile) {
                    void useDbProfileStore.getState().loadProfile();
                }
            } else {
                pushBot({ content: '<p>⚠️ The pipeline returned no result.</p>' });
            }
        } catch (err: unknown) {
            if (err instanceof Error && err.name === 'AbortError') {
                pushBot({ content: '<p>⚠️ Request cancelled.</p>' });
            } else {
                pushBot({
                    content: '<p>⚠️ Could not connect to the backend. Is it running on port 5000?</p>',
                });
            }
        } finally {
            set({ isWaiting: false });
            useProgressStore.getState().reset();
            abortController = null;
        }
    },

    stop: () => {
        abortController?.abort();
    },

    newChat: () => {
        chatEpoch += 1;
        // Cancel any in-flight stream first — its finally block clears isWaiting.
        abortController?.abort();
        useSessionStore.getState().setActiveSession(null);
        useProgressStore.getState().reset();
        set({ messages: [INITIAL_MESSAGE], isWaiting: false });
    },

    // KI-1 resolved: assistant turns (answers *and* clarification questions) are
    // persisted by the backend and reconstructed here as restored bot messages.
    // Sessions recorded before that persistence landed only contain user turns
    // and will restore as questions-only — expected for legacy data.
    loadFromSession: detail => {
        const messages: Message[] = detail.turns.map(turn =>
            turn.role === 'user'
                ? { id: turn.turn_id, role: 'user' as const, content: turn.content }
                : {
                      id: turn.turn_id,
                      role: 'bot' as const,
                      content: '',
                      restored: true,
                      result: {
                          type: 'result' as const,
                          session_id: detail.session_id,
                          teaching_summary: turn.content,
                          sql: turn.sql ? { sql: turn.sql } : null,
                          rows: safeParseRows(turn.rows_json),
                          // Sentinel: stored turns keep only the first 10 rows,
                          // so the true count is unknown.
                          row_count: -1,
                          intent: null,
                          verify: null,
                          error: null,
                      },
                  },
        );
        set({ messages: messages.length > 0 ? messages : [INITIAL_MESSAGE] });
    },
}));
