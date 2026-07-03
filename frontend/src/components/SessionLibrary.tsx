import { useEffect, useState } from 'react';
import { fetchSession } from '../services/api';
import { useSessionStore } from '../stores/sessionStore';
import { useQueryStore } from '../stores/queryStore';
import styles from './SessionLibrary.module.css';

interface SessionLibraryProps {
    /** Called after a session is loaded into the chat (closes the drawer). */
    onClose: () => void;
}

function formatWhen(iso: string): string {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function SessionLibrary({ onClose }: SessionLibraryProps) {
    const sessions = useSessionStore(s => s.sessions);
    const activeSessionId = useSessionStore(s => s.activeSessionId);
    const isLoading = useSessionStore(s => s.isLoading);
    const error = useSessionStore(s => s.error);
    const [loadError, setLoadError] = useState<string | null>(null);

    useEffect(() => {
        void useSessionStore.getState().refreshSessions();
    }, []);

    const openSession = async (id: string) => {
        setLoadError(null);
        try {
            const detail = await fetchSession(id);
            useSessionStore.getState().setActiveSession(id);
            useQueryStore.getState().loadFromSession(detail);
            onClose();
        } catch {
            setLoadError('Could not load that session.');
        }
    };

    if (error) return <p className={styles.error}>{error}</p>;
    if (isLoading && sessions.length === 0) return <p className={styles.empty}>Loading sessions…</p>;
    if (sessions.length === 0) {
        return <p className={styles.empty}>No sessions yet — run a query to start one.</p>;
    }

    return (
        <div className={styles.list}>
            {loadError && <p className={styles.error}>{loadError}</p>}
            {sessions.map(s => (
                <button
                    key={s.session_id}
                    type="button"
                    className={
                        s.session_id === activeSessionId
                            ? `${styles.item} ${styles.itemActive}`
                            : styles.item
                    }
                    onClick={() => void openSession(s.session_id)}
                >
                    <span className={styles.itemTitle}>{s.title || 'Untitled session'}</span>
                    <span className={styles.itemMeta}>
                        {s.db_name} · {formatWhen(s.updated_at)}
                        {s.session_id === activeSessionId ? ' · active' : ''}
                    </span>
                </button>
            ))}
        </div>
    );
}
