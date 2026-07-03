import { create } from 'zustand';
import {
    DatabaseSummary,
    fetchAvailableDatabases,
    fetchLastUsedDatabase,
    selectDatabase,
} from '../services/api';
import { useDbProfileStore } from './dbProfileStore';

interface DatabaseState {
    databases: DatabaseSummary[];
    /** Set once a database has been successfully selected — gates the app shell. */
    activeDbName: string | null;
    /** From the most recent session's db_name; null if no prior sessions exist. */
    lastUsedDbName: string | null;
    isLoading: boolean;
    error: string | null;
    loadDatabases: () => Promise<void>;
    loadLastUsed: () => Promise<void>;
    chooseDatabase: (dbName: string) => Promise<void>;
}

export const useDatabaseStore = create<DatabaseState>(set => ({
    databases: [],
    activeDbName: null,
    lastUsedDbName: null,
    isLoading: false,
    error: null,

    loadDatabases: async () => {
        set({ isLoading: true, error: null });
        try {
            const databases = await fetchAvailableDatabases();
            set({ databases, isLoading: false });
        } catch {
            set({
                error: 'Could not load databases — is the backend running?',
                isLoading: false,
            });
        }
    },

    loadLastUsed: async () => {
        try {
            const lastUsedDbName = await fetchLastUsedDatabase();
            set({ lastUsedDbName });
        } catch {
            set({ lastUsedDbName: null });
        }
    },

    chooseDatabase: async dbName => {
        set({ isLoading: true, error: null });
        try {
            const profile = await selectDatabase(dbName);
            useDbProfileStore.setState({ profile, fetched: true });
            set({ activeDbName: dbName, isLoading: false });
        } catch {
            set({ error: `Could not load database "${dbName}".`, isLoading: false });
        }
    },
}));
