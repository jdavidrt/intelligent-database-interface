import { useCallback, useEffect, useRef, useState } from 'react';

const BACKEND = 'http://localhost:5000';
const POLL_MS = 2000;

// ── types ─────────────────────────────────────────────────────────────────────

interface QueryMetrics {
    completion_tokens: number;
    time_ms: number;
}

interface Correctness {
    score: number;
    has_sql: boolean;
    found_tables: string[];
    missing_tables: string[];
    found_keywords: string[];
    missing_keywords: string[];
}

interface QueryResult {
    id: string;
    title: string;
    query: string;
    response: string;
    metrics: QueryMetrics | null;
    correctness: Correctness;
    error: string | null;
}

interface BenchmarkJob {
    id: string;
    mode: 'gpu' | 'cpu';
    status: 'running' | 'done' | 'error';
    phase: 'init' | 'switching' | 'running';
    stage_label: string;
    progress: number;
    total: number;
    results: QueryResult[];
    error: string | null;
}

type ModeKey = 'gpu' | 'cpu';

interface ModeState {
    jobId: string | null;
    job: BenchmarkJob | null;
    loading: boolean;
}

// ── helpers ───────────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
    const color =
        score >= 80 ? 'var(--score-good)' :
        score >= 50 ? 'var(--score-mid)' :
                      'var(--score-bad)';
    return (
        <div className="score-bar-wrap">
            <div
                className="score-bar-fill"
                style={{ width: `${score}%`, background: color }}
            />
            <span className="score-label" style={{ color }}>{score}%</span>
        </div>
    );
}

function fmt(ms: number): string {
    if (ms >= 60000) return `${(ms / 60000).toFixed(1)} min`;
    if (ms >= 1000)  return `${(ms / 1000).toFixed(1)} s`;
    return `${ms} ms`;
}

// ── single result row ─────────────────────────────────────────────────────────

function ResultRow({
    result,
    index,
    otherResult,
}: {
    result: QueryResult | undefined;
    index: number;
    otherResult: QueryResult | undefined;
}) {
    const [expanded, setExpanded] = useState(false);
    const hasResult = !!result;

    return (
        <div className={`bench-row ${index % 2 === 0 ? 'bench-row-even' : ''}`}>
            <div className="bench-row-header" onClick={() => hasResult && setExpanded(e => !e)}>
                <div className="bench-row-index">{index + 1}</div>
                <div className="bench-row-title">{result?.title ?? otherResult?.title ?? `Query ${index + 1}`}</div>

                {/* GPU column */}
                <div className="bench-cell">
                    {result ? (
                        result.error ? (
                            <span className="bench-err">Error</span>
                        ) : (
                            <>
                                <span className="bench-metric">{fmt(result.metrics?.time_ms ?? 0)}</span>
                                <span className="bench-metric-sub">{result.metrics?.completion_tokens ?? 0} tok</span>
                                <ScoreBar score={result.correctness.score} />
                            </>
                        )
                    ) : (
                        <span className="bench-pending">—</span>
                    )}
                </div>

                {/* Expand toggle */}
                {hasResult && (
                    <button className="bench-expand-btn" aria-label="Toggle response">
                        {expanded ? '▲' : '▼'}
                    </button>
                )}
            </div>

            {expanded && result && (
                <div className="bench-detail">
                    {result.error ? (
                        <p className="bench-detail-error">{result.error}</p>
                    ) : (
                        <>
                            <div className="bench-detail-meta">
                                <span>Time: <strong>{fmt(result.metrics?.time_ms ?? 0)}</strong></span>
                                <span>Tokens: <strong>{result.metrics?.completion_tokens ?? 0}</strong></span>
                                <span>Score: <strong>{result.correctness.score}%</strong></span>
                                {!result.correctness.has_sql && (
                                    <span className="bench-warn">No SQL block found</span>
                                )}
                            </div>
                            {result.correctness.missing_tables.length > 0 && (
                                <div className="bench-detail-missing">
                                    Missing tables: <span>{result.correctness.missing_tables.join(', ')}</span>
                                </div>
                            )}
                            {result.correctness.missing_keywords.length > 0 && (
                                <div className="bench-detail-missing">
                                    Missing keywords: <span>{result.correctness.missing_keywords.join(', ')}</span>
                                </div>
                            )}
                            <pre className="bench-response">{result.response}</pre>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

// ── comparison table ──────────────────────────────────────────────────────────

const QUERY_IDS = ['mid-level', 'simple', 'subquery', 'cte-window', 'analytical'];

function ComparisonTable({
    gpuJob,
    cpuJob,
}: {
    gpuJob: BenchmarkJob | null;
    cpuJob: BenchmarkJob | null;
}) {
    const hasAny = gpuJob || cpuJob;
    if (!hasAny) return null;

    return (
        <div className="bench-table-wrap">
            <div className="bench-table-header">
                <div className="bench-th bench-th-index">#</div>
                <div className="bench-th bench-th-title">Query</div>
                <div className="bench-th bench-th-mode">
                    <span className="mode-badge gpu-badge">🚀 GPU</span>
                    Time · Tokens · Score
                </div>
                <div className="bench-th bench-th-mode">
                    <span className="mode-badge cpu-badge">🖥 CPU</span>
                    Time · Tokens · Score
                </div>
                <div className="bench-th bench-th-expand" />
            </div>

            {QUERY_IDS.map((qid, i) => {
                const gpuRes = gpuJob?.results.find(r => r.id === qid);
                const cpuRes = cpuJob?.results.find(r => r.id === qid);
                return (
                    <ComparisonRow
                        key={qid}
                        index={i}
                        gpuResult={gpuRes}
                        cpuResult={cpuRes}
                    />
                );
            })}
        </div>
    );
}

function ComparisonRow({
    index,
    gpuResult,
    cpuResult,
}: {
    index: number;
    gpuResult: QueryResult | undefined;
    cpuResult: QueryResult | undefined;
}) {
    const [expanded, setExpanded] = useState(false);
    const either = gpuResult ?? cpuResult;
    const hasAny = !!either;

    return (
        <div className={`bench-row ${index % 2 === 0 ? 'bench-row-even' : ''}`}>
            <div
                className="bench-row-header"
                onClick={() => hasAny && setExpanded(e => !e)}
                style={{ cursor: hasAny ? 'pointer' : 'default' }}
            >
                <div className="bench-th-index bench-row-index">{index + 1}</div>
                <div className="bench-th-title bench-row-title">{either?.title ?? `Query ${index + 1}`}</div>

                {/* GPU cell */}
                <div className="bench-cell bench-th-mode">
                    <ResultCell result={gpuResult} />
                </div>

                {/* CPU cell */}
                <div className="bench-cell bench-th-mode">
                    <ResultCell result={cpuResult} />
                </div>

                <div className="bench-th-expand">
                    {hasAny && (
                        <button className="bench-expand-btn" aria-label="Toggle details">
                            {expanded ? '▲' : '▼'}
                        </button>
                    )}
                </div>
            </div>

            {expanded && either && (
                <div className="bench-detail">
                    <div className="bench-detail-cols">
                        <ExpandedDetail label="🚀 GPU" result={gpuResult} />
                        <ExpandedDetail label="🖥 CPU" result={cpuResult} />
                    </div>
                </div>
            )}
        </div>
    );
}

function ResultCell({ result }: { result: QueryResult | undefined }) {
    if (!result) return <span className="bench-pending">—</span>;
    if (result.error) return <span className="bench-err">Error</span>;
    return (
        <div className="result-cell-inner">
            <span className="bench-metric">{fmt(result.metrics?.time_ms ?? 0)}</span>
            <span className="bench-metric-sub">{result.metrics?.completion_tokens ?? 0} tok</span>
            <ScoreBar score={result.correctness.score} />
        </div>
    );
}

function ExpandedDetail({
    label,
    result,
}: {
    label: string;
    result: QueryResult | undefined;
}) {
    if (!result) {
        return (
            <div className="expanded-col">
                <div className="expanded-col-label">{label}</div>
                <p className="bench-pending">Not yet run.</p>
            </div>
        );
    }
    return (
        <div className="expanded-col">
            <div className="expanded-col-label">{label}</div>
            {result.error ? (
                <p className="bench-detail-error">{result.error}</p>
            ) : (
                <>
                    <div className="bench-detail-meta">
                        <span>Time: <strong>{fmt(result.metrics?.time_ms ?? 0)}</strong></span>
                        <span>Tokens: <strong>{result.metrics?.completion_tokens ?? 0}</strong></span>
                        <span>Score: <strong>{result.correctness.score}%</strong></span>
                    </div>
                    {result.correctness.missing_tables.length > 0 && (
                        <div className="bench-detail-missing">
                            Missing tables: <span>{result.correctness.missing_tables.join(', ')}</span>
                        </div>
                    )}
                    {result.correctness.missing_keywords.length > 0 && (
                        <div className="bench-detail-missing">
                            Missing keywords: <span>{result.correctness.missing_keywords.join(', ')}</span>
                        </div>
                    )}
                    <pre className="bench-response">{result.response}</pre>
                </>
            )}
        </div>
    );
}

// ── mode card ─────────────────────────────────────────────────────────────────

function ModeCard({
    mode,
    step,
    modeState,
    onRun,
    blocked,
}: {
    mode: ModeKey;
    step: 1 | 2;
    modeState: ModeState;
    onRun: (mode: ModeKey) => void;
    /** true when the OTHER mode is currently running */
    blocked: boolean;
}) {
    const isGpu = mode === 'gpu';
    const { job, loading } = modeState;
    const isRunning = loading || job?.status === 'running';
    const isDone    = job?.status === 'done';
    const isError   = job?.status === 'error';

    return (
        <div className={`mode-card ${isGpu ? 'mode-card-gpu' : 'mode-card-cpu'} ${isDone ? 'mode-card-done' : ''}`}>
            <div className="mode-card-step">Step {step}</div>
            <div className="mode-card-icon">{isGpu ? '🚀' : '🖥'}</div>
            <div className="mode-card-title">{isGpu ? 'GPU Mode' : 'CPU Mode'}</div>
            <div className="mode-card-sub">
                {isGpu ? 'llama.cpp  -ngl 99  (all layers on VRAM)' : 'llama.cpp  -ngl 0  (RAM + CPU only)'}
            </div>

            <button
                className={`mode-run-btn ${isGpu ? 'mode-run-gpu' : 'mode-run-cpu'}`}
                disabled={isRunning || blocked}
                title={blocked ? 'Wait for the other benchmark to finish first.' : undefined}
                onClick={() => onRun(mode)}
            >
                {isRunning
                    ? 'Running…'
                    : blocked
                    ? '⏳ Waiting…'
                    : isDone
                    ? `↺ Re-run ${isGpu ? 'GPU' : 'CPU'}`
                    : `▶ Run ${isGpu ? 'GPU' : 'CPU'} Benchmark`}
            </button>

            {isRunning && (
                <div className="mode-progress">
                    <div className="mode-progress-bar">
                        <div
                            className="mode-progress-fill"
                            style={{
                                width: job
                                    ? `${Math.round((job.progress / job.total) * 100)}%`
                                    : '5%',
                            }}
                        />
                    </div>
                    <div className="mode-progress-label">{job?.stage_label}</div>
                </div>
            )}

            {isDone && (
                <div className="mode-done">✓ Complete — {job.results.length} / 5 queries</div>
            )}
            {isError && (
                <div className="mode-error">✗ {job?.error}</div>
            )}
        </div>
    );
}

// ── main page ─────────────────────────────────────────────────────────────────

export function BenchmarksPage() {
    const [gpuState, setGpuState] = useState<ModeState>({ jobId: null, job: null, loading: false });
    const [cpuState, setCpuState] = useState<ModeState>({ jobId: null, job: null, loading: false });

    const gpuPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const cpuPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stopPoll = (ref: React.MutableRefObject<ReturnType<typeof setInterval> | null>) => {
        if (ref.current) { clearInterval(ref.current); ref.current = null; }
    };

    const pollJob = useCallback(
        async (
            jobId: string,
            setState: React.Dispatch<React.SetStateAction<ModeState>>,
            pollRef: React.MutableRefObject<ReturnType<typeof setInterval> | null>,
        ) => {
            try {
                const res = await fetch(`${BACKEND}/benchmark/status/${jobId}`);
                if (!res.ok) return;
                const job: BenchmarkJob = await res.json();
                setState(prev => ({ ...prev, job, loading: false }));
                if (job.status === 'done' || job.status === 'error') {
                    stopPoll(pollRef);
                }
            } catch {
                // network blip — keep polling
            }
        },
        [],
    );

    const handleRun = useCallback(
        async (mode: ModeKey) => {
            const setState = mode === 'gpu' ? setGpuState : setCpuState;
            const pollRef = mode === 'gpu' ? gpuPollRef : cpuPollRef;

            stopPoll(pollRef);
            setState({ jobId: null, job: null, loading: true });

            try {
                const res = await fetch(`${BACKEND}/benchmark/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode }),
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const { job_id } = await res.json();

                setState(prev => ({ ...prev, jobId: job_id }));

                pollRef.current = setInterval(
                    () => pollJob(job_id, setState, pollRef),
                    POLL_MS,
                );
            } catch (e: unknown) {
                const msg = e instanceof Error ? e.message : 'Unknown error';
                setState({
                    jobId: null,
                    loading: false,
                    job: {
                        id: '',
                        mode,
                        status: 'error',
                        phase: 'init',
                        stage_label: '',
                        progress: 0,
                        total: 5,
                        results: [],
                        error: `Could not start benchmark: ${msg}`,
                    },
                });
            }
        },
        [pollJob],
    );

    // cleanup on unmount
    useEffect(() => {
        return () => {
            stopPoll(gpuPollRef);
            stopPoll(cpuPollRef);
        };
    }, []);

    const gpuJob = gpuState.job;
    const cpuJob = cpuState.job;
    const hasAnyResults =
        (gpuJob?.results.length ?? 0) > 0 || (cpuJob?.results.length ?? 0) > 0;

    const cpuRunning = cpuState.loading || cpuState.job?.status === 'running';
    const gpuRunning = gpuState.loading || gpuState.job?.status === 'running';

    return (
        <div className="bench-page">
            <div className="bench-header">
                <h2 className="bench-title">Performance Benchmarks</h2>
                <p className="bench-subtitle">
                    Run all 5 queries consecutively — first on <strong>CPU</strong>, then on <strong>GPU</strong>.
                    Each run restarts llama.cpp in the selected mode before firing the queries.
                    <br />
                    <span className="bench-warning">
                        ⚠ Each run temporarily restarts the llama.cpp server. Chat will be unavailable during the benchmark.
                    </span>
                </p>
            </div>

            <div className="mode-cards">
                <ModeCard mode="cpu" step={1} modeState={cpuState} onRun={handleRun} blocked={gpuRunning} />
                <ModeCard mode="gpu" step={2} modeState={gpuState} onRun={handleRun} blocked={cpuRunning} />
            </div>

            {hasAnyResults && (
                <div className="bench-results-section">
                    <h3 className="bench-results-title">Results</h3>
                    <ComparisonTable gpuJob={gpuJob} cpuJob={cpuJob} />
                </div>
            )}

            {!hasAnyResults && (
                <div className="bench-empty">
                    Run a benchmark above to see results here.
                </div>
            )}
        </div>
    );
}
