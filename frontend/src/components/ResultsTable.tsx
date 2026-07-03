interface ResultsTableProps {
    rows: Array<Record<string, unknown>>;
    /** Total rows returned by the query; -1 when unknown (restored session preview). */
    rowCount: number;
    limit?: number;
    /** Optional caption rendered above the table (e.g. restored-preview notice). */
    note?: string;
}

export function ResultsTable({ rows, rowCount, limit = 50, note }: ResultsTableProps) {
    if (rows.length === 0) {
        return <p className="result-empty">Query ran successfully — 0 rows returned.</p>;
    }

    const cols = Object.keys(rows[0]);
    const shown = rows.slice(0, limit);
    const hidden = rowCount === -1 ? 0 : rows.length - shown.length;

    return (
        <>
            {note && <div className="result-more">{note}</div>}
            <div className="result-table-wrap">
                <table className="result-table">
                    <thead>
                        <tr>
                            {cols.map(c => (
                                <th key={c}>{c}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {shown.map((row, i) => (
                            <tr key={i}>
                                {cols.map(c => {
                                    const v = row[c];
                                    return (
                                        <td key={c}>
                                            {v === null || v === undefined ? '∅' : String(v)}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {hidden > 0 && <div className="result-more">… {hidden} more row(s)</div>}
        </>
    );
}
