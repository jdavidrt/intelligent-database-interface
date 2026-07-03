import { create } from 'zustand';
import { AgentEvent, AgentName } from '../services/api';

export interface ProgressStep {
    agent: AgentName;
    status: AgentEvent['status'];
    message: string;
    /**
     * Instruction profile active for this agent's turn (from payload.adapter).
     * undefined = no adapter event seen; null = base model (fail-safe semantics).
     */
    adapter?: string | null;
}

interface ProgressState {
    /** Latest status+message per agent, in first-seen order. */
    steps: ProgressStep[];
    addEvent: (ev: AgentEvent) => void;
    reset: () => void;
}

export const useProgressStore = create<ProgressState>(set => ({
    steps: [],

    // Merge per agent rather than replace: the adapter arrives on a 'progress'
    // event ("Adapter active") that precedes the agent's 'done' event, and must
    // survive it.
    addEvent: ev =>
        set(state => {
            const adapter =
                ev.payload && 'adapter' in ev.payload
                    ? (ev.payload.adapter as string | null)
                    : undefined;

            const idx = state.steps.findIndex(s => s.agent === ev.agent);
            if (idx === -1) {
                return {
                    steps: [
                        ...state.steps,
                        { agent: ev.agent, status: ev.status, message: ev.message, adapter },
                    ],
                };
            }

            const next = [...state.steps];
            next[idx] = {
                ...next[idx],
                status: ev.status,
                message: ev.message,
                ...(adapter !== undefined ? { adapter } : {}),
            };
            return { steps: next };
        }),

    reset: () => set({ steps: [] }),
}));
