import { create } from 'zustand';
import { fetchSessions, SessionSummary } from '../services/api';

interface SessionState {
    /** Reused across turns so the pipeline gets multi-turn history + clarification replies. */
    activeSessionId: string | null;
    sessions: SessionSummary[];
    isLoading: boolean;
    error: string | null;
    setActiveSession: (id: string | null) => void;
    refreshSessions: () => Promise<void>;
}

export const useSessionStore = create<SessionState>(set => ({
    activeSessionId: null,
    sessions: [],
    isLoading: false,
    error: null,

    setActiveSession: id => set({ activeSessionId: id }),

    refreshSessions: async () => {
        set({ isLoading: true, error: null });
        try {
            const sessions = await fetchSessions();
            set({ sessions, isLoading: false });
        } catch {
            set({
                error: 'Could not load sessions — is the backend running?',
                isLoading: false,
            });
        }
    },
}));
