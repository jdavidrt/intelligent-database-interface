import { useEffect } from 'react';
import { DBColumn } from '../services/api';
import { useDbProfileStore } from '../stores/dbProfileStore';
import styles from './DBProfileForm.module.css';

// Read-only "map of the database" (Delta 2). The editable survey — writing
// corrections back — is deferred to Day 4, when an unknown database can appear.

function columnBadges(col: DBColumn, sensitive: boolean) {
    return (
        <>
            {col.is_primary_key && <span className={styles.badge}>PK</span>}
            {col.is_foreign_key && (
                <span className={`${styles.badge} ${styles.badgeFk}`}>FK</span>
            )}
            {sensitive && <span title="Sensitive column">🔒</span>}
        </>
    );
}

function sampleText(values: unknown[]): string {
    if (values.length === 0) return '';
    const joined = values.slice(0, 4).map(v => String(v)).join(', ');
    return joined.length > 60 ? `${joined.slice(0, 57)}…` : joined;
}

export function DBProfileForm() {
    const profile = useDbProfileStore(s => s.profile);
    const fetched = useDbProfileStore(s => s.fetched);

    // Cheap retry on open — the profile may have been built since app mount.
    useEffect(() => {
        if (!profile) void useDbProfileStore.getState().loadProfile();
    }, [profile]);

    if (!fetched && !profile) {
        return <p className={styles.placeholder}>Loading the database profile…</p>;
    }

    if (!profile) {
        return (
            <p className={styles.placeholder}>
                No profile yet — run a query to build the database map.
            </p>
        );
    }

    const glossary = Object.entries(profile.glossary);
    const codedMaps = Object.entries(profile.coded_value_maps);
    const sourceOfTruth = Object.entries(profile.source_of_truth);

    return (
        <div className={styles.card}>
            <section>
                <h3 className={styles.dbName}>{profile.db_name}</h3>
                {profile.domain_description && (
                    <p className={styles.domainText}>{profile.domain_description}</p>
                )}
            </section>

            <section>
                <h4 className={styles.sectionTitle}>Tables ({profile.tables.length})</h4>
                {profile.tables.map(table => (
                    <details key={table.name} className={styles.table}>
                        <summary>
                            {table.name}
                            <span className={styles.tableMeta}>
                                {table.columns.length} column(s)
                                {table.row_count !== null && ` · ${table.row_count} row(s)`}
                            </span>
                        </summary>
                        {table.description && (
                            <p className={styles.tableDesc}>{table.description}</p>
                        )}
                        <div className={styles.colTableWrap}>
                            <table className={styles.colTable}>
                                <thead>
                                    <tr>
                                        <th>Column</th>
                                        <th>Type</th>
                                        <th>Notes</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {table.columns.map(col => (
                                        <tr key={col.name}>
                                            <td>
                                                {columnBadges(col, Boolean(profile.sensitivity[col.name]))}
                                                {col.name}
                                            </td>
                                            <td className={styles.colNote}>
                                                {col.data_type}
                                                {col.is_nullable ? '' : ' · not null'}
                                            </td>
                                            <td className={styles.colNote}>
                                                {col.references && <div>→ {col.references}</div>}
                                                {col.glossary_note && <div>{col.glossary_note}</div>}
                                                {col.sample_values.length > 0 && (
                                                    <div>e.g. {sampleText(col.sample_values)}</div>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </details>
                ))}
            </section>

            {glossary.length > 0 && (
                <section>
                    <h4 className={styles.sectionTitle}>Glossary</h4>
                    <dl className={styles.dl}>
                        {glossary.map(([abbrev, meaning]) => (
                            <div key={abbrev} style={{ display: 'contents' }}>
                                <dt>{abbrev}</dt>
                                <dd>{meaning}</dd>
                            </div>
                        ))}
                    </dl>
                </section>
            )}

            {codedMaps.length > 0 && (
                <section>
                    <h4 className={styles.sectionTitle}>Coded values</h4>
                    {codedMaps.map(([column, mapping]) => (
                        <div key={column} className={styles.codedGroup}>
                            <div className={styles.chipCol}>{column}</div>
                            <div className={styles.chips}>
                                {Object.entries(mapping).map(([code, meaning]) => (
                                    <span key={code} className={styles.chip}>
                                        {code} → {meaning}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </section>
            )}

            {sourceOfTruth.length > 0 && (
                <section>
                    <h4 className={styles.sectionTitle}>Source of truth</h4>
                    <dl className={styles.dl}>
                        {sourceOfTruth.map(([column, description]) => (
                            <div key={column} style={{ display: 'contents' }}>
                                <dt>{column}</dt>
                                <dd>{description}</dd>
                            </div>
                        ))}
                    </dl>
                </section>
            )}
        </div>
    );
}
