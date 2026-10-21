import { useCallback, useEffect, useRef, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Clock3,
  FileSpreadsheet,
  History,
  Plus,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../api";
import type { Job, JobList } from "../api";
import {
  dateLabel,
  durationLabel,
  filename,
  operationLabel,
  resultExpired,
} from "../utils";
import { Status } from "./Status";

export function JobsHistory({
  onOpen,
  onReuse,
  onCreate,
  onError,
  onCount,
}: {
  onOpen: (job: Job) => void;
  onReuse: (job: Job) => void;
  onCreate: () => void;
  onError: (message: string) => void;
  onCount: (count: number) => void;
}) {
  const [search, setSearch] = useState(""),
    [query, setQuery] = useState(""),
    [status, setStatus] = useState("");
  const [page, setPage] = useState(1),
    [data, setData] = useState<JobList | null>(null),
    [loading, setLoading] = useState(true);
  const sequence = useRef(0);
  const handlers = useRef({ onError, onCount });
  handlers.current = { onError, onCount };
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      setQuery(search.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);
  const load = useCallback(
    async (quiet = false) => {
      const current = ++sequence.current;
      if (!quiet) setLoading(true);
      try {
        const next = await api.jobs({
          page,
          limit: 5,
          kind: "transform",
          status,
          search: query,
        });
        if (sequence.current !== current) return;
        if (page > 1 && !next.jobs.length) {
          setPage(Math.max(1, Math.ceil(next.total / 5)));
          return;
        }
        setData(next);
        if (!query && !status) handlers.current.onCount(next.total);
      } catch (error) {
        if (sequence.current === current)
          handlers.current.onError(
            error instanceof Error ? error.message : "Unable to load jobs.",
          );
      } finally {
        if (sequence.current === current) setLoading(false);
      }
    },
    [page, status, query],
  );
  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(true), 8000);
    return () => {
      sequence.current++;
      clearInterval(timer);
    };
  }, [load]);
  function clear() {
    setSearch("");
    setQuery("");
    setStatus("");
    setPage(1);
  }
  return (
    <>
      <section className="panel" aria-busy={loading}>
        <div className="history-toolbar">
          <div className="search-field">
            <Search />
            <input
              type="search"
              aria-label="Search jobs"
              placeholder="Search file name or job ID"
              maxLength={128}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            aria-label="Filter jobs"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            <option value="QUEUED">Queued</option>
            <option value="RUNNING">Running</option>
            <option value="SUCCESS">Succeeded</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="expired">Results expired</option>
          </select>
          {(search || status) && (
            <button className="link" onClick={clear}>
              Clear
            </button>
          )}
          <button
            className="icon-button"
            aria-label="Refresh jobs"
            disabled={loading}
            onClick={() => void load()}
          >
            <RefreshCw className={loading ? "spin" : ""} />
          </button>
        </div>
        {loading && !data ? (
          <div className="empty" role="status">
            Loading jobs…
          </div>
        ) : !data ? (
          <div className="empty">
            <p>Jobs could not be loaded.</p>
            <button onClick={() => void load()}>Try again</button>
          </div>
        ) : !data.jobs.length ? (
          <div className="empty">
            <History />
            <h2>{query || status ? "No matching jobs" : "No jobs yet"}</h2>
            <p>
              {query || status
                ? "Try a different file name, job ID or status."
                : "Connect a source, describe a change and run your first transformation. Your jobs will appear here."}
            </p>
            <button onClick={query || status ? clear : onCreate}>
              {query || status ? (
                "Clear filters"
              ) : (
                <>
                  <Plus />
                  Prepare data
                </>
              )}
            </button>
          </div>
        ) : (
          <>
            <div className="table-wrap">
              <table className="history-table" aria-label="Job history">
                <colgroup>
                  <col style={{ width: "26%" }} />
                  <col style={{ width: "16%" }} />
                  <col style={{ width: "18%" }} />
                  <col style={{ width: "16%" }} />
                  <col style={{ width: "8%" }} />
                  <col style={{ width: "16%" }} />
                </colgroup>
                <thead>
                  <tr>
                    {[
                      "Source / Job",
                      "Operation",
                      "Status",
                      "Created",
                      "Duration",
                      "Actions",
                    ].map((title) => (
                      <th key={title}>{title}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.jobs.map((job) => {
                    const date = dateLabel(job.created_at).split(",");
                    return (
                      <tr key={job.id}>
                        <td>
                          <button
                            className="link history-file"
                            title={job.source_key}
                            onClick={() => onOpen(job)}
                          >
                            <FileSpreadsheet />
                            <span>{filename(job.source_key)}</span>
                          </button>
                          <div className="history-meta" title={job.id}>
                            {job.id.slice(0, 8)}
                            {job.source_type === "sample"
                              ? " · Simulated S3"
                              : ""}
                            {job.sheet ? ` · ${job.sheet}` : ""}
                          </div>
                        </td>
                        <td>{operationLabel(job.operation)}</td>
                        <td>
                          <Status job={job} />
                          {job.status === "SUCCESS" && (
                            <div
                              className={`history-meta ${resultExpired(job) ? "expired" : ""}`}
                            >
                              {resultExpired(job)
                                ? "Results expired"
                                : "Results available"}
                            </div>
                          )}
                        </td>
                        <td className="date-cell">
                          {date[0]}
                          <div className="history-meta">
                            {date.slice(1).join(",").trim()}
                          </div>
                        </td>
                        <td className="date-cell">{durationLabel(job)}</td>
                        <td>
                          <div className="history-actions">
                            <button
                              className="link"
                              onClick={() => onOpen(job)}
                            >
                              View
                            </button>
                            <button
                              className="link"
                              onClick={() => onReuse(job)}
                            >
                              Reuse
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="table-bottom">
              <span>
                {(page - 1) * 5 + 1}–{Math.min(page * 5, data.total)} of{" "}
                {data.total} jobs
              </span>
              <div className="pagination" aria-label="Job history pagination">
                <button
                  className="icon-button"
                  aria-label="Previous jobs"
                  disabled={page === 1 || loading}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft />
                </button>
                <span>
                  Page {page} of {Math.max(1, Math.ceil(data.total / 5))}
                </span>
                <button
                  className="icon-button"
                  aria-label="Next jobs"
                  disabled={!data.has_next || loading}
                  onClick={() => setPage(page + 1)}
                >
                  <ChevronRight />
                </button>
              </div>
            </div>
          </>
        )}
      </section>
      <div className="history-footer">
        <span>
          <Clock3 /> Results are available for 24 hours.
        </span>
        <span>Times in Sydney · Current guest session</span>
      </div>
    </>
  );
}
