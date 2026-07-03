import { create } from 'zustand';
import { DBProfile, fetchDbProfile } from '../services/api';

interface DbProfileState {
    profile: DBProfile | null;
    /** True once at least one fetch attempt completed (distinguishes loading from 404). */
    fetched: boolean;
    loadProfile: () => Promise<void>;
}

export const useDbProfileStore = create<DbProfileState>(set => ({
    profile: null,
    fetched: false,

    // The backend builds the profile lazily on the first query, so a 404
    // (fetchDbProfile → null) is an expected state, never an error.
    loadProfile: async () => {
        try {
            const profile = await fetchDbProfile();
            set({ profile, fetched: true });
        } catch {
            set({ fetched: true });
        }
    },
}));
