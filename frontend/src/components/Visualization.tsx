import type { ReactNode } from 'react';
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ResponsiveContainer,
    Scatter,
    ScatterChart,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts';
import styles from './Visualization.module.css';

type Row = Record<string, unknown>;

const SERIES_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)'];
const MAX_CHART_ROWS = 50;
const MAX_SERIES = 3;
const MAX_CATEGORIES = 20;
const MAX_COLUMNS = 6;

// The wire serializes Decimals/datetimes as strings (json.dumps default=str).
const NUMERIC_RE = /^-?\d+(\.\d+)?$/;
const TEMPORAL_RE = /^\d{4}-\d{2}-\d{2}/;

const compactNumber = new Intl.NumberFormat('en', { notation: 'compact' });
const fullNumber = new Intl.NumberFormat('en');

function isNumericValue(v: unknown): boolean {
    return typeof v === 'number' || (typeof v === 'string' && NUMERIC_RE.test(v));
}

function isTemporalValue(v: unknown): boolean {
    return typeof v === 'string' && TEMPORAL_RE.test(v);
}

interface ColumnKinds {
    numeric: string[];
    temporal: string[];
    categorical: string[];
}

function classifyColumns(rows: Row[]): ColumnKinds {
    const kinds: ColumnKinds = { numeric: [], temporal: [], categorical: [] };
    for (const col of Object.keys(rows[0])) {
        const values = rows.map(r => r[col]).filter(v => v !== null && v !== undefined);
        if (values.length === 0) {
            kinds.categorical.push(col);
        } else if (values.every(isNumericValue)) {
            kinds.numeric.push(col);
        } else if (values.every(isTemporalValue)) {
            kinds.temporal.push(col);
        } else {
            kinds.categorical.push(col);
        }
    }
    return kinds;
}

function toNumber(v: unknown): number {
    return typeof v === 'number' ? v : Number(v);
}

// ── shared chart chrome (text wears text tokens, grid/axes recessive) ──────────

const TICK_STYLE = { fill: 'var(--text-dim)', fontSize: 12 };
const AXIS_LINE = { stroke: 'var(--glass-border)' };
const TOOLTIP_PROPS = {
    contentStyle: {
        background: 'var(--card-bg)',
        border: '1px solid var(--glass-border)',
        borderRadius: 'var(--radius-sm)',
        backdropFilter: 'blur(8px)',
    },
    labelStyle: { color: 'var(--text)' },
    itemStyle: { color: 'var(--text)' },
    cursor: { fill: 'var(--input-bg-focus)' },
};

const legendText = (value: string) => (
    <span style={{ color: 'var(--text)', fontSize: 12 }}>{value}</span>
);

// ── forms ───────────────────────────────────────────────────────────────────────

function StatTiles({ row, cols }: { row: Row; cols: string[] }) {
    return (
        <div className={styles.statRow}>
            {cols.slice(0, MAX_SERIES).map(col => (
                <div key={col} className={styles.statTile}>
                    <div className={styles.statValue}>
                        {fullNumber.format(toNumber(row[col]))}
                    </div>
                    <div className={styles.statLabel}>{col}</div>
                </div>
            ))}
        </div>
    );
}

function TimeLine({ rows, xCol, yCols }: { rows: Row[]; xCol: string; yCols: string[] }) {
    const data = rows
        .map(r => {
            const point: Row = { [xCol]: String(r[xCol]) };
            for (const c of yCols) point[c] = toNumber(r[c]);
            return point;
        })
        // ISO date strings sort correctly lexicographically.
        .sort((a, b) => String(a[xCol]).localeCompare(String(b[xCol])));

    return (
        <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                <XAxis
                    dataKey={xCol}
                    tick={TICK_STYLE}
                    axisLine={AXIS_LINE}
                    tickLine={false}
                    tickFormatter={(v: string) => v.slice(0, 10)}
                />
                <YAxis
                    tick={TICK_STYLE}
                    axisLine={AXIS_LINE}
                    tickLine={false}
                    tickFormatter={(v: number) => compactNumber.format(v)}
                    width={48}
                />
                <Tooltip {...TOOLTIP_PROPS} cursor={{ stroke: 'var(--glass-border)' }} />
                {yCols.length > 1 && <Legend formatter={legendText} />}
                {yCols.map((c, i) => (
                    <Line
                        key={c}
                        type="monotone"
                        dataKey={c}
                        stroke={SERIES_COLORS[i]}
                        strokeWidth={2}
                        dot={{ r: 3, fill: SERIES_COLORS[i], strokeWidth: 0 }}
                        activeDot={{ r: 5 }}
                    />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}

function CategoryBars({ rows, xCol, yCols }: { rows: Row[]; xCol: string; yCols: string[] }) {
    const data = rows.map(r => {
        const point: Row = { [xCol]: String(r[xCol]) };
        for (const c of yCols) point[c] = toNumber(r[c]);
        return point;
    });

    const avgLabelLen =
        data.reduce((sum, r) => sum + String(r[xCol]).length, 0) / (data.length || 1);
    const horizontal = avgLabelLen > 12 || data.length > 8;

    return (
        <ResponsiveContainer width="100%" height={horizontal ? Math.max(260, data.length * 32) : 260}>
            <BarChart
                data={data}
                layout={horizontal ? 'vertical' : 'horizontal'}
                margin={{ top: 8, right: 16, bottom: 4, left: 4 }}
            >
                <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="var(--glass-border)"
                    vertical={horizontal}
                    horizontal={!horizontal}
                />
                {horizontal ? (
                    <>
                        <XAxis
                            type="number"
                            tick={TICK_STYLE}
                            axisLine={AXIS_LINE}
                            tickLine={false}
                            tickFormatter={(v: number) => compactNumber.format(v)}
                        />
                        <YAxis
                            type="category"
                            dataKey={xCol}
                            tick={TICK_STYLE}
                            axisLine={AXIS_LINE}
                            tickLine={false}
                            width={140}
                        />
                    </>
                ) : (
                    <>
                        <XAxis
                            dataKey={xCol}
                            tick={TICK_STYLE}
                            axisLine={AXIS_LINE}
                            tickLine={false}
                        />
                        <YAxis
                            tick={TICK_STYLE}
                            axisLine={AXIS_LINE}
                            tickLine={false}
                            tickFormatter={(v: number) => compactNumber.format(v)}
                            width={48}
                        />
                    </>
                )}
                <Tooltip {...TOOLTIP_PROPS} />
                {yCols.length > 1 && <Legend formatter={legendText} />}
                {yCols.map((c, i) => (
                    <Bar
                        key={c}
                        dataKey={c}
                        fill={SERIES_COLORS[i]}
                        radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]}
                        maxBarSize={36}
                    />
                ))}
            </BarChart>
        </ResponsiveContainer>
    );
}

function NumericScatter({ rows, xCol, yCol }: { rows: Row[]; xCol: string; yCol: string }) {
    const data = rows.map(r => ({ [xCol]: toNumber(r[xCol]), [yCol]: toNumber(r[yCol]) }));

    return (
        <ResponsiveContainer width="100%" height={260}>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
                <XAxis
                    type="number"
                    dataKey={xCol}
                    name={xCol}
                    tick={TICK_STYLE}
                    axisLine={AXIS_LINE}
                    tickLine={false}
                    tickFormatter={(v: number) => compactNumber.format(v)}
                />
                <YAxis
                    type="number"
                    dataKey={yCol}
                    name={yCol}
                    tick={TICK_STYLE}
                    axisLine={AXIS_LINE}
                    tickLine={false}
                    tickFormatter={(v: number) => compactNumber.format(v)}
                    width={48}
                />
                <Tooltip {...TOOLTIP_PROPS} cursor={{ stroke: 'var(--glass-border)' }} />
                <Scatter data={data} fill="var(--chart-1)" />
            </ScatterChart>
        </ResponsiveContainer>
    );
}

// ── auto-chart entry point ──────────────────────────────────────────────────────

/**
 * Heuristic chart selection over the result rows. Renders nothing when no form
 * fits — the ResultsTable below is always the complement, never replaced.
 */
export function Visualization({ rows }: { rows: Row[] }) {
    if (rows.length === 0) return null;

    const cols = Object.keys(rows[0]);
    if (cols.length > MAX_COLUMNS) return null;

    const sample = rows.slice(0, MAX_CHART_ROWS);
    const { numeric, temporal, categorical } = classifyColumns(sample);

    let chart: ReactNode = null;
    let caption: string | null = null;

    if (rows.length === 1 && numeric.length >= 1) {
        chart = <StatTiles row={rows[0]} cols={numeric} />;
    } else if (temporal.length >= 1 && numeric.length >= 1) {
        chart = (
            <TimeLine rows={sample} xCol={temporal[0]} yCols={numeric.slice(0, MAX_SERIES)} />
        );
        caption = `${numeric.slice(0, MAX_SERIES).join(', ')} over ${temporal[0]}`;
    } else if (
        categorical.length >= 1 &&
        numeric.length >= 1 &&
        new Set(sample.map(r => String(r[categorical[0]]))).size <= MAX_CATEGORIES
    ) {
        chart = (
            <CategoryBars rows={sample} xCol={categorical[0]} yCols={numeric.slice(0, MAX_SERIES)} />
        );
        caption = `${numeric.slice(0, MAX_SERIES).join(', ')} by ${categorical[0]}`;
    } else if (numeric.length >= 2 && categorical.length === 0) {
        chart = <NumericScatter rows={sample} xCol={numeric[0]} yCol={numeric[1]} />;
        caption = `${numeric[1]} vs ${numeric[0]}`;
    }

    if (!chart) return null;

    return (
        <div className={styles.chartWrap}>
            {caption && (
                <div className={styles.chartCaption}>
                    {caption}
                    {rows.length > MAX_CHART_ROWS ? ` — first ${MAX_CHART_ROWS} rows charted` : ''}
                </div>
            )}
            {chart}
        </div>
    );
}
