import type { ReactNode } from 'react';
import { QueryResult } from '../services/api';
import { highlightSQL } from '../utils/sqlHighlighter';
import { renderMarkdown } from '../utils/markdownRenderer';
import { ResultsTable } from './ResultsTable';
import { Visualization } from './Visualization';
import styles from './AnswerPanel.module.css';

interface AnswerPanelProps {
    result: QueryResult;
    /** Reconstructed from stored turns: teaching summary replaces What/Why, chart suppressed. */
    restored?: boolean;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
    return (
        <section className={styles.section}>
            <h3 className={styles.heading}>{title}</h3>
            <div className={styles.body}>{children}</div>
        </section>
    );
}

export function AnswerPanel({ result, restored = false }: AnswerPanelProps) {
    const sql = result.sql?.sql ?? null;
    const verify = result.verify ?? null;
    const restatement = result.intent?.plain_restatement ?? null;
    const rationale = result.sql?.rationale ?? null;

    // No SQL and no error: clarification branch (or empty fallback) — the
    // teaching summary carries the whole answer (e.g. the follow-up question).
    if (!sql && !result.error) {
        return (
            <div className={styles.answer}>
                {result.teaching_summary ? (
                    <div
                        className="section-body"
                        dangerouslySetInnerHTML={{
                            __html: renderMarkdown(result.teaching_summary),
                        }}
                    />
                ) : (
                    <p>No response produced.</p>
                )}
            </div>
        );
    }

    const layers = verify
        ? ([
              ['Syntax', verify.syntax],
              ['Semantic', verify.semantic],
              ['Sanity', verify.sanity],
          ] as const)
        : [];

    return (
        <div className={styles.answer}>
            {restatement && (
                <Section title="What I understood">
                    <p className={styles.restatement}>{restatement}</p>
                </Section>
            )}

            {restored && result.teaching_summary && (
                <Section title="The lesson">
                    <div
                        dangerouslySetInnerHTML={{
                            __html: renderMarkdown(result.teaching_summary),
                        }}
                    />
                </Section>
            )}

            {sql && (
                <Section title="The SQL">
                    <pre>
                        <code
                            className="lang-sql"
                            dangerouslySetInnerHTML={{ __html: highlightSQL(sql) }}
                        />
                    </pre>
                    {verify?.repaired_sql && verify.repaired_sql !== sql && (
                        <>
                            <span className={styles.sqlLabel}>
                                Repaired by the Verification Agent — this is what actually ran:
                            </span>
                            <pre>
                                <code
                                    className="lang-sql"
                                    dangerouslySetInnerHTML={{
                                        __html: highlightSQL(verify.repaired_sql),
                                    }}
                                />
                            </pre>
                        </>
                    )}
                </Section>
            )}

            {(rationale || verify) && (
                <Section title="Why this query">
                    {rationale && <p>{rationale}</p>}
                    {layers.length > 0 && (
                        <ul className={styles.verifyList}>
                            {layers.map(([name, layer]) => (
                                <li
                                    key={name}
                                    className={layer.passed ? styles.verifyPass : styles.verifyFail}
                                >
                                    <span className={styles.verifyIcon}>
                                        {layer.passed ? '✓' : '✗'}
                                    </span>
                                    <span className={styles.verifyLayer}>{name}</span>
                                    <span className={styles.verifyMsg}>{layer.message}</span>
                                </li>
                            ))}
                        </ul>
                    )}
                    {verify?.repair_explanation && (
                        <p className={styles.repairNote}>🔧 {verify.repair_explanation}</p>
                    )}
                </Section>
            )}

            {result.error && (
                <div className={styles.errorBanner}>⚠️ {result.error}</div>
            )}

            {!result.error && sql && (
                <Section title="Results">
                    {!restored && <Visualization rows={result.rows} />}
                    <ResultsTable
                        rows={result.rows}
                        rowCount={result.row_count}
                        note={
                            restored
                                ? 'Restored preview — first 10 rows of the original result.'
                                : undefined
                        }
                    />
                </Section>
            )}
        </div>
    );
}
