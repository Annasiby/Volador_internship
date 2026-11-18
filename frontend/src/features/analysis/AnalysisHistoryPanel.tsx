import React, { useEffect, useState, useCallback } from "react";
import { useProject } from "../../context/useProject";
import { getProjectRuns, type ProjectRunItem, getPdfReportUrl } from "../../api/client";

interface Props {
    onNavigate?: (tab: string) => void;
}

export default function AnalysisHistoryPanel({ onNavigate }: Props) {
    const { project, runStatus, selectRun } = useProject() as any;

    const [runs, setRuns] = useState<ProjectRunItem[]>([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [page, setPage] = useState(0);
    const limit = 10;

    const fetchHistory = useCallback(async () => {
        if (!project?.id) return;
        try {
            setLoading(true);
            setError(null);
            const data = await getProjectRuns(project.id, limit, page * limit);
            setRuns(data.runs);
            setTotal(data.total);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Failed to load run history");
        } finally {
            setLoading(false);
        }
    }, [project?.id, page]);

    // Refresh on mount, page change, or when an active run finishes/launches
    useEffect(() => {
        fetchHistory();
    }, [fetchHistory, runStatus?.status]);

    const handleSelect = async (run: ProjectRunItem) => {
        if (run.status !== "COMPLETED") return;
        if (selectRun) {
            await selectRun(run.run_id);
            if (onNavigate) onNavigate("Results");
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "COMPLETED":
                return <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-medium text-emerald-400 border border-emerald-500/20">Completed</span>;
            case "FAILED":
                return <span className="rounded-full bg-rose-500/10 px-2.5 py-0.5 text-[11px] font-medium text-rose-400 border border-rose-500/20">Failed</span>;
            default:
                return <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-400 border border-amber-500/20 animate-pulse">{status}</span>;
        }
    };

    return (
        <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
            <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
                <div>
                    <h3 className="text-sm font-medium text-[var(--text)]">Analysis History</h3>
                    <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                        Past runs and outcomes for this project ({total} total)
                    </p>
                </div>
                <button
                    onClick={fetchHistory}
                    disabled={loading}
                    className="rounded border border-[var(--border)] px-2.5 py-1 text-xs text-[var(--text-secondary)] hover:text-[var(--text)] hover:bg-[var(--background)] transition-colors"
                >
                    {loading ? "Refreshing..." : "↻ Refresh"}
                </button>
            </div>

            {/* Loading State */}
            {loading && runs.length === 0 && (
                <div className="py-8 text-center text-xs text-[var(--text-secondary)]">
                    Loading history...
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="mt-4 rounded-md border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
                    {error}
                </div>
            )}

            {/* Empty State */}
            {!loading && !error && runs.length === 0 && (
                <div className="py-8 text-center text-xs text-[var(--text-secondary)]">
                    No analysis runs recorded yet. Run your first analysis above to see history here.
                </div>
            )}

            {/* Populated List */}
            {runs.length > 0 && (
                <div className="mt-4 divide-y divide-[var(--border)]">
                    {runs.map((run) => {
                        const isCompleted = run.status === "COMPLETED";
                        const isFailed = run.status === "FAILED";
                        const isSelected = runStatus?.run_id === run.run_id;

                        return (
                            <div
                                key={run.run_id}
                                onClick={() => isCompleted && handleSelect(run)}
                                className={`flex flex-col gap-2 py-3.5 transition-colors ${isCompleted
                                        ? "cursor-pointer hover:bg-[var(--background)]/50 rounded-md px-2"
                                        : "cursor-default px-2"
                                    } ${isSelected ? "border-l-2 border-[var(--accent)] bg-[var(--accent)]/5 pl-3" : ""}`}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-xs font-semibold text-[var(--text)]">{run.run_id}</span>
                                        <span className="rounded bg-[var(--background)] px-1.5 py-0.5 text-[10px] text-[var(--text-secondary)] uppercase">
                                            {run.mode || "unknown"} {run.mode_inferred ? "(inferred)" : ""}
                                        </span>
                                        {isSelected && (
                                            <span className="rounded bg-[var(--accent)]/20 px-1.5 py-0.5 text-[10px] text-[var(--accent)] font-medium">
                                                Active
                                            </span>
                                        )}
                                    </div>
                                    <div>{getStatusBadge(run.status)}</div>
                                </div>

                                <div className="flex items-center justify-between text-[11px] text-[var(--text-secondary)]">
                                    <span>
                                        Started: {run.started_at ? new Date(run.started_at).toLocaleString() : (run.created_at ? new Date(run.created_at).toLocaleString() : "—")}
                                    </span>
                                    {run.t1_date && (
                                        <span>
                                            Dates: {run.t1_date} {run.t2_date ? `→ ${run.t2_date}` : ""}
                                        </span>
                                    )}
                                </div>

                                {/* Concise Error message for failed runs */}
                                {isFailed && run.error && (
                                    <div className="rounded bg-rose-500/10 p-2 text-xs text-rose-400">
                                        Failure: {run.error}
                                    </div>
                                )}

                                {/* Actions for completed runs */}
                                {isCompleted && (
                                    <div className="mt-1 flex items-center gap-3 text-xs">
                                        <span className="text-[var(--accent)] hover:underline font-medium">
                                            Open Results →
                                        </span>
                                        <a
                                            href={getPdfReportUrl(run.run_id)}
                                            target="_blank"
                                            rel="noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                            className="text-[var(--text-secondary)] hover:text-[var(--text)] hover:underline"
                                        >
                                            PDF Report ↗
                                        </a>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Pagination Controls */}
            {total > limit && (
                <div className="mt-4 flex items-center justify-between border-t border-[var(--border)] pt-3 text-xs text-[var(--text-secondary)]">
                    <span>
                        Page {page + 1} of {Math.ceil(total / limit)}
                    </span>
                    <div className="flex gap-2">
                        <button
                            disabled={page === 0}
                            onClick={() => setPage((p) => p - 1)}
                            className="rounded border border-[var(--border)] px-2.5 py-1 disabled:opacity-40"
                        >
                            Previous
                        </button>
                        <button
                            disabled={(page + 1) * limit >= total}
                            onClick={() => setPage((p) => p + 1)}
                            className="rounded border border-[var(--border)] px-2.5 py-1 disabled:opacity-40"
                        >
                            Next
                        </button>
                    </div>
                </div>
            )}
        </section>
    );
}