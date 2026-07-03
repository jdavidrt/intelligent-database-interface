import type { ReactNode } from 'react';
import { createPortal } from 'react-dom';
import styles from './Drawer.module.css';

interface DrawerProps {
    title: string;
    onClose: () => void;
    children: ReactNode;
}

/**
 * Right-side overlay panel shared by SessionLibrary and DBProfileForm.
 * Rendered via a portal: .container's backdrop-filter/transform would otherwise
 * turn it into the containing block for position: fixed.
 */
export function Drawer({ title, onClose, children }: DrawerProps) {
    return createPortal(
        <aside className={styles.drawer}>
            <div className={styles.header}>
                <h2 className={styles.title}>{title}</h2>
                <button
                    type="button"
                    className={styles.closeBtn}
                    aria-label="Close panel"
                    onClick={onClose}
                >
                    ✕
                </button>
            </div>
            <div className={styles.body}>{children}</div>
        </aside>,
        document.body,
    );
}
