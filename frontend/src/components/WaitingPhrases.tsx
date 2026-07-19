import { useEffect, useState } from 'react';
import styles from './WaitingPhrases.module.css';

/** Short didactic facts about databases/SQL, rotated while the pipeline runs.
 *  No time-remaining estimate by design (MASTERPLAN §Pending backlog). */
const PHRASES = [
    'SQL was born at IBM in the 1970s as "SEQUEL" — Structured English Query Language.',
    'A JOIN doesn\'t copy data — it matches rows from two tables on a shared key.',
    'Indexes are like a book\'s table of contents: they trade disk space for lookup speed.',
    'NULL is not zero or empty text — it means "unknown", and NULL = NULL is never true.',
    'GROUP BY collapses rows that share a value so aggregates like COUNT or AVG can summarize them.',
    'A primary key uniquely identifies each row; a foreign key points at another table\'s primary key.',
    'The query optimizer rewrites your SQL into the cheapest execution plan it can find.',
    'LIMIT trims the result set — the database may still scan far more rows to build it.',
    'Transactions are all-or-nothing: either every change commits, or none of them do (the "A" in ACID).',
    'WHERE filters rows before grouping; HAVING filters groups after aggregation.',
    'A view is a saved query that behaves like a virtual table.',
    'Normalization splits data into tables to avoid duplication; JOINs put it back together.',
    'ORDER BY is usually one of the last steps — sorting happens after filtering and grouping.',
    'SELECT * is handy for exploring, but production queries name their columns explicitly.',
];

const ROTATE_MS = 8000;

export function WaitingPhrases() {
    // Start at a random phrase so consecutive queries don't always show the same one.
    const [index, setIndex] = useState(() => Math.floor(Math.random() * PHRASES.length));

    useEffect(() => {
        const id = setInterval(() => {
            setIndex(i => (i + 1) % PHRASES.length);
        }, ROTATE_MS);
        return () => clearInterval(id);
    }, []);

    return (
        <div className={styles.container} role="status" aria-live="polite">
            <span className={styles.label}>💡 While you wait</span>
            <p className={styles.phrase} key={index}>
                {PHRASES[index]}
            </p>
        </div>
    );
}
