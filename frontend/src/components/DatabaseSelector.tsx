import { useEffect } from 'react';
import { useDatabaseStore } from '../stores/databaseStore';
import styles from './DatabaseSelector.module.css';

// The landing screen shown before the chat UI — the user must pick a database
// (context is built once here, not lazily per query) before anything else loads.
export function DatabaseSelector() {
    const databases = useDatabaseStore(s => s.databases);
    const lastUsedDbName = useDatabaseStore(s => s.lastUsedDbName);
    const isLoading = useDatabaseStore(s => s.isLoading);
    const error = useDatabaseStore(s => s.error);

    useEffect(() => {
        void useDatabaseStore.getState().loadDatabases();
        void useDatabaseStore.getState().loadLastUsed();
    }, []);

    const choose = (dbName: string) => {
        void useDatabaseStore.getState().chooseDatabase(dbName);
    };

    return (
        <div className={styles.screen}>
            <h1 className={styles.heading}>Select the database you want to work with…</h1>

            {lastUsedDbName && (
                <button
                    type="button"
                    className={styles.shortcutBtn}
                    disabled={isLoading}
                    onClick={() => choose(lastUsedDbName)}
                >
                    Use the last database used ({lastUsedDbName})
                </button>
            )}

            {error && <p className={styles.error}>{error}</p>}
            {isLoading && <p className={styles.placeholder}>Loading…</p>}

            <div className={styles.list}>
                {databases.map(db => (
                    <button
                        key={db.db_name}
                        type="button"
                        className={styles.card}
                        disabled={isLoading}
                        onClick={() => choose(db.db_name)}
                    >
                        <span className={styles.dbTitle}>{db.display_name}</span>
                        {db.description && <span className={styles.dbDesc}>{db.description}</span>}
                    </button>
                ))}
            </div>

            {!isLoading && databases.length === 0 && !error && (
                <p className={styles.placeholder}>No databases found under databases/.</p>
            )}
        </div>
    );
}
