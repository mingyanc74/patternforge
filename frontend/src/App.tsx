import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  Cloud,
  Code2,
  Copy,
  Database,
  FileSpreadsheet,
  FolderOpen,
  Layers3,
  LayoutDashboard,
  ListChecks,
  LoaderCircle,
  LockKeyhole,
  Play,
  PlugZap,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Square,
  Terminal,
  WandSparkles,
  X,
  XCircle,
} from "lucide-react";
import { api, RequestError } from "./api";
import type {
  Bootstrap,
  Column,
  Connection,
  Job,
  Operation,
  ResultPage,
  SourceFile,
} from "./api";
import { active, filename, formatBytes, stageLabels } from "./utils";

const operations: {
  id: Operation;
  title: string;
  description: string;
  icon: typeof WandSparkles;
}[] = [
  {
    id: "regex_replace",
    title: "Find & replace",
    description: "Replace patterns in your text",
    icon: WandSparkles,
  },
  {
    id: "regex_extract",
    title: "Extract a field",
    description: "Turn a pattern into a new column",
    icon: ArrowUpRight,
  },
  {
    id: "normalize",
    title: "Clean & standardize",
    description: "Make text consistent",
    icon: ListChecks,
  },
];
const suggestions: Record<Operation, { label: string; text: string }[]> = {
  regex_replace: [
    { label: "Email addresses", text: "Find all email addresses." },
    {
      label: "Phone numbers",
      text: "Find phone numbers including optional country codes.",
    },
    {
      label: "Order IDs",
      text: "Find order IDs starting with ORD- followed by digits.",
    },
  ],
  regex_extract: [
    {
      label: "Order IDs",
      text: "Extract the first order ID starting with ORD- followed by digits.",
    },
    { label: "Email addresses", text: "Extract the first email address." },
  ],
  normalize: [
    {
      label: "Clean names",
      text: "Trim leading and trailing whitespace and collapse consecutive whitespace.",
    },
    {
      label: "Lowercase text",
      text: "Trim whitespace, collapse repeated whitespace, then convert to lowercase.",
    },
    {
      label: "Uppercase codes",
      text: "Trim whitespace and convert to uppercase.",
    },
  ],
};

function usePolling(
  job: Job | null,
  setJob: (job: Job) => void,
  onError: (message: string) => void,
) {
  useEffect(() => {
    if (!active(job)) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;
    const poll = async () => {
      try {
        const result = await api.job(job!.id);
        if (stopped) return;
        failures = 0;
        onError("");
        setJob(result);
        if (active(result)) timer = setTimeout(poll, 2000);
      } catch (error) {
        if (stopped) return;
        failures++;
        onError(
          error instanceof Error ? error.message : "Connection interrupted.",
        );
        timer = setTimeout(poll, Math.min(15000, 2000 * 2 ** failures));
      }
    };
    timer = setTimeout(poll, 1000);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status, setJob, onError]);
}

function Status({ job }: { job: Job }) {
  return (
    <span className={`status ${job.status.toLowerCase()}`}>
      {active(job) ? (
        <LoaderCircle size={12} className="spin" />
      ) : job.status === "SUCCESS" ? (
        <Check size={12} />
      ) : null}
      {job.cancel_requested && active(job)
        ? "Cancelling"
        : job.stage === "RETRYING"
          ? "Retrying"
          : {
              QUEUED: "Queued",
              RUNNING: "Running",
              SUCCESS: "Complete",
              FAILED: "Failed",
              CANCELLED: "Cancelled",
            }[job.status]}
    </span>
  );
}

function DataTable({
  rows,
  columns,
  selected = [],
}: {
  rows: Record<string, unknown>[];
  columns: Column[];
  selected?: string[];
}) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th className="row-number">#</th>
            {columns.map((column) => (
              <th key={column.name}>
                <span className="type-mark">Aa</span>
                {column.name}
                {selected.includes(column.name) && (
                  <span className="column-dot" title="Target column" />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              <td className="row-number">{index + 1}</td>
              {columns.map((column) => (
                <td
                  key={column.name}
                  title={
                    row[column.name] == null ? "null" : String(row[column.name])
                  }
                >
                  {row[column.name] == null ? (
                    <span className="null-value">null</span>
                  ) : row[column.name] === "" ? (
                    <span className="null-value">empty</span>
                  ) : (
                    String(row[column.name]).slice(0, 250)
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [boot, setBoot] = useState<Bootstrap | null>(null);
  const [ready, setReady] = useState(false);
  const [services, setServices] = useState<Record<string, boolean>>({});
  const [view, setView] = useState<"workspace" | "activity">("workspace");
  const [guide, setGuide] = useState(false);
  const [error, setError] = useState("");
  const [network, setNetwork] = useState("");
  const [connection, setConnection] = useState<Connection | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [credentials, setCredentials] = useState({
    bucket: "",
    region: "us-east-1",
    access_key: "",
    secret_key: "",
    session_token: "",
  });
  const [connecting, setConnecting] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [files, setFiles] = useState<SourceFile[]>([]);
  const [prefix, setPrefix] = useState("");
  const [fileCursor, setFileCursor] = useState<string | null>(null);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [selected, setSelected] = useState<SourceFile | null>(null);
  const [sheet, setSheet] = useState("");
  const [delimiter, setDelimiter] = useState(",");
  const [encoding, setEncoding] = useState("UTF-8");
  const [inspection, setInspection] = useState<Job | null>(null);
  const [operation, setOperation] = useState<Operation>("regex_replace");
  const [prompt, setPrompt] = useState("");
  const [columns, setColumns] = useState<string[]>([]);
  const [replacement, setReplacement] = useState("REDACTED");
  const [newColumn, setNewColumn] = useState("extracted_value");
  const [job, setJob] = useState<Job | null>(null);
  const [history, setHistory] = useState<Job[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState<ResultPage | null>(null);
  const [cursors, setCursors] = useState<string[]>([""]);
  const [pageNumber, setPageNumber] = useState(0);
  const [pageSize, setPageSize] = useState(100);
  const [loadingPage, setLoadingPage] = useState(false);
  const [copied, setCopied] = useState(false);
  const submitKey = useRef(crypto.randomUUID());
  const currentJobId = useRef<string | undefined>(undefined);
  currentJobId.current = job?.id;
  const processing = active(job) || active(inspection);
  const report = useCallback(
    (e: unknown) =>
      setError(
        e instanceof Error ? e.message : "Something went wrong. Please retry.",
      ),
    [],
  );

  usePolling(inspection, setInspection, setNetwork);
  usePolling(job, setJob, setNetwork);

  const loadFiles = useCallback(
    async (item: Connection, path: string, cursor = "", append = false) => {
      setLoadingFiles(true);
      setError("");
      try {
        const result = await api.files(item.id, path, cursor);
        setFiles((old) => (append ? [...old, ...result.files] : result.files));
        setFileCursor(result.next_cursor);
      } catch (e) {
        report(e);
      } finally {
        setLoadingFiles(false);
      }
    },
    [report],
  );

  const initialize = useCallback(async () => {
    setError("");
    try {
      const config = await api.bootstrap();
      setBoot(config);
      setReady(true);
      const [saved, jobs, health] = await Promise.all([
        api.connections(),
        api.jobs(),
        api.health(),
      ]);
      setConnections(saved.connections);
      setHistory(jobs.jobs);
      setServices(health.services);
      const matched = location.hash.match(/^#job=([a-f0-9-]{36})$/i);
      if (matched) {
        const resumed = await api.job(matched[1]);
        const linked = saved.connections.find(
          (item) => item.id === resumed.connection_id,
        );
        if (linked) {
          setConnection(linked);
          setSelected({
            key: resumed.source_key,
            size: 0,
            modified: resumed.created_at,
            supported: true,
          });
          void loadFiles(linked, "");
        }
        const config = resumed.config || {};
        setSheet(String(config.sheet || ""));
        setDelimiter(String(config.delimiter || ","));
        setEncoding(String(config.encoding || "UTF-8"));
        if (resumed.kind === "inspect") setInspection(resumed);
        else {
          setJob(resumed);
          setOperation(config.operation as Operation);
          setPrompt(String(config.prompt || ""));
          setColumns((config.target_columns as string[]) || []);
          setReplacement(String(config.replacement ?? ""));
          setNewColumn(String(config.new_column || "extracted_value"));
          if (config.inspection_id)
            void api
              .job(String(config.inspection_id))
              .then(setInspection)
              .catch(() => {});
        }
      } else if (saved.connections.length) {
        setConnection(saved.connections[0]);
        void loadFiles(saved.connections[0], "");
      }
    } catch (e) {
      report(e);
    }
  }, [loadFiles, report]);
  useEffect(() => {
    void initialize();
  }, [initialize]);
  useEffect(() => {
    if (job || inspection)
      void api
        .jobs()
        .then((result) => setHistory(result.jobs))
        .catch(() => {});
  }, [job?.status, inspection?.status]);

  const loadPage = useCallback(
    async (current: Job, cursor: string, index: number) => {
      setLoadingPage(true);
      setError("");
      try {
        const next = await api.results(current.id, cursor, pageSize);
        if (currentJobId.current === current.id) {
          setPage(next);
          setPageNumber(index);
        }
      } catch (e) {
        report(e);
      } finally {
        setLoadingPage(false);
      }
    },
    [pageSize, report],
  );
  useEffect(() => {
    if (job?.status === "SUCCESS" && job.result_available) {
      setCursors([""]);
      void loadPage(job, "", 0);
    }
  }, [job?.id, job?.status, job?.result_available, loadPage]);
  useEffect(() => {
    submitKey.current = crypto.randomUUID();
  }, [
    connection?.id,
    selected?.key,
    sheet,
    delimiter,
    encoding,
    operation,
    prompt,
    columns,
    replacement,
    newColumn,
  ]);
  useEffect(() => {
    if (!guide) return;
    const previous = document.activeElement as HTMLElement | null;
    const modal = document.querySelector<HTMLElement>(".guide-modal");
    const elements = () =>
      Array.from(
        modal?.querySelectorAll<HTMLElement>(
          "button, summary, input, a[href]",
        ) || [],
      ).filter((element) => !element.hasAttribute("disabled"));
    elements()[0]?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setGuide(false);
      if (event.key === "Tab") {
        const items = elements();
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, [guide]);

  async function connect(event: React.FormEvent) {
    event.preventDefault();
    setConnecting(true);
    setError("");
    try {
      const result = await api.connect(credentials);
      setConnection(result);
      setConnections((old) => [result, ...old]);
      setCredentials((old) => ({
        ...old,
        access_key: "",
        secret_key: "",
        session_token: "",
      }));
      setSelected(null);
      setInspection(null);
      setJob(null);
      setPage(null);
      setPrefix("");
      await loadFiles(result, "");
    } catch (e) {
      report(e);
    } finally {
      setConnecting(false);
    }
  }
  function chooseFile(file: SourceFile) {
    setSelected(file);
    setInspection(null);
    setJob(null);
    setPage(null);
    setColumns([]);
    setSheet("");
    setError("");
    window.history.replaceState(null, "", location.pathname);
  }
  async function inspectFile() {
    if (!connection || !selected) return;
    setSubmitting(true);
    setError("");
    setColumns([]);
    setPage(null);
    setJob(null);
    try {
      const result = await api.inspect({
        connection_id: connection.id,
        source_key: selected.key,
        sheet,
        delimiter,
        encoding,
      });
      setInspection(result);
    } catch (e) {
      report(e);
    } finally {
      setSubmitting(false);
    }
  }
  const schema =
    inspection?.status === "SUCCESS" && !inspection.metadata?.requires_sheet
      ? inspection.metadata?.columns || []
      : [];
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!connection || !selected || !inspection || !schema.length) return;
    setSubmitting(true);
    setError("");
    setPage(null);
    const body = {
      connection_id: connection.id,
      source_key: selected.key,
      inspection_id: inspection.id,
      sheet: inspection.metadata?.sheet || sheet,
      delimiter,
      encoding,
      operation,
      prompt,
      target_columns: columns,
      ...(operation === "regex_replace" ? { replacement } : {}),
      ...(operation === "regex_extract" ? { new_column: newColumn } : {}),
    };
    try {
      const result = await api.createJob(body, submitKey.current);
      setJob(result);
      window.history.replaceState(null, "", "#job=" + result.id);
      submitKey.current = crypto.randomUUID();
    } catch (e) {
      report(e);
      if (e instanceof RequestError && e.code !== "NETWORK_ERROR")
        submitKey.current = crypto.randomUUID();
    } finally {
      setSubmitting(false);
    }
  }
  async function cancel(current: Job) {
    try {
      const result = await api.cancel(current.id);
      current.kind === "inspect" ? setInspection(result) : setJob(result);
    } catch (e) {
      report(e);
    }
  }
  async function openJob(item: Job) {
    setError("");
    try {
      const result = await api.job(item.id);
      if (result.kind === "inspect") setInspection(result);
      else {
        setJob(result);
        setPage(null);
        setInspection(null);
        setSelected(null);
      }
      setView("workspace");
      window.history.replaceState(null, "", "#job=" + item.id);
    } catch (e) {
      report(e);
    }
  }
  const current = active(inspection) ? inspection : job;
  const tableRows = page?.rows || inspection?.metadata?.preview || [];
  const tableColumns = page?.columns || schema;
  const transformation = operations.find((item) => item.id === operation)!;
  const changed = Object.values(job?.metadata?.changed_cells || {}).reduce(
    (a, b) => a + b,
    0,
  );
  const steps = [!!connection, !!schema.length, job?.status === "SUCCESS"];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("workspace");
          }}
        >
          <span className="brand-mark">
            <Layers3 size={22} />
          </span>
          PatternForge
          <span className="brand-dot" />
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={view === "workspace" ? "nav-item selected" : "nav-item"}
            onClick={() => setView("workspace")}
          >
            <LayoutDashboard size={18} />
            Data workspace
          </button>
          <button
            className={view === "activity" ? "nav-item selected" : "nav-item"}
            onClick={() => setView("activity")}
          >
            <Clock3 size={18} />
            Activity
            <span className="nav-count">
              {history.filter((item) => item.kind === "transform").length}
            </span>
          </button>
          <button className="nav-item" onClick={() => setGuide(true)}>
            <BookOpen size={18} />
            Quick guide
            <ArrowUpRight size={14} className="nav-arrow" />
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card">
            <ShieldCheck size={22} />
            <strong>Your data, protected.</strong>
            <p>
              Credentials are encrypted. Your original files stay untouched.
            </p>
          </div>
          <div className="profile">
            <span>PF</span>
            <div>
              <strong>Private session</strong>
              <small>This browser only</small>
            </div>
            <LockKeyhole size={14} />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            Workspace <ChevronRight size={14} />
            <strong>
              {view === "workspace" ? "Data transformation" : "Activity"}
            </strong>
          </div>
          <div className="topbar-actions">
            <span
              className={`service-light ${services.queue && services.worker && services.spark ? "online" : ""}`}
            />
            {services.queue && services.worker && services.spark
              ? "Processing service online"
              : "Service setup required"}
            <button
              className="icon-button"
              aria-label="Help"
              onClick={() => setGuide(true)}
            >
              <CircleHelp size={19} />
            </button>
            <span className="avatar">M</span>
          </div>
        </header>
        <div className="page-content">
          <div className="page-heading">
            <div className="eyebrow">
              <span /> NATURAL LANGUAGE. STRUCTURED RESULTS.
            </div>
            <h1>
              {view === "workspace"
                ? "Make your data work for you."
                : "Your processing activity."}
            </h1>
            <p>
              {view === "workspace"
                ? "Connect your S3 bucket, describe a change, and let your data do the rest."
                : "Track recent jobs, recover a running task, and revisit completed results."}
            </p>
          </div>
          {error && (
            <div className="alert error" role="alert">
              <XCircle size={18} />
              <div>
                <strong>Action needed</strong>
                <p>{error}</p>
              </div>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {network && (
            <div className="alert warning" role="status">
              <RefreshCw size={17} />
              <p>
                Reconnecting to task updates. Processing may still be running.
              </p>
            </div>
          )}
          {!ready && (
            <div className="alert warning">
              <Terminal size={18} />
              <div>
                <strong>Connect the application service</strong>
                <p>
                  The workspace is waiting for the backend. Start the app, then
                  retry.
                </p>
              </div>
              <button
                className="button secondary small"
                onClick={() => void initialize()}
              >
                Retry connection
              </button>
            </div>
          )}
          {ready && !boot?.llm_configured && (
            <div className="alert info">
              <PlugZap size={18} />
              <div>
                <strong>One setup step before your first transformation</strong>
                <p>
                  The administrator needs to connect a language model. You can
                  still connect S3 and inspect your files.
                </p>
              </div>
              <button className="text-button" onClick={() => setGuide(true)}>
                Setup guide <ArrowRight size={14} />
              </button>
            </div>
          )}

          {view === "activity" ? (
            <section className="card activity-card">
              <div className="card-header">
                <div>
                  <span className="section-kicker">PROCESSING HISTORY</span>
                  <h2>Recent jobs</h2>
                </div>
                <button
                  className="button secondary small"
                  onClick={() =>
                    void api
                      .jobs()
                      .then((result) => setHistory(result.jobs))
                      .catch(report)
                  }
                >
                  <RefreshCw size={14} />
                  Refresh
                </button>
              </div>
              {!history.length ? (
                <div className="empty-state">
                  <Clock3 size={34} />
                  <h3>A fresh start</h3>
                  <p>Your inspections and transformations will appear here.</p>
                  <button
                    className="button primary"
                    onClick={() => setView("workspace")}
                  >
                    Open workspace <ArrowRight size={15} />
                  </button>
                </div>
              ) : (
                <div className="table-scroll">
                  <table className="activity-table">
                    <thead>
                      <tr>
                        <th>Source file</th>
                        <th>Task</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((item) => (
                        <tr key={item.id}>
                          <td title={item.source_key}>
                            <FileSpreadsheet size={16} />
                            {filename(item.source_key)}
                          </td>
                          <td>
                            {item.kind === "inspect"
                              ? "File inspection"
                              : "Transformation"}
                          </td>
                          <td>
                            <Status job={item} />
                          </td>
                          <td>{new Date(item.created_at).toLocaleString()}</td>
                          <td>
                            <button
                              className="text-button"
                              onClick={() => void openJob(item)}
                            >
                              Open <ArrowUpRight size={14} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ) : (
            <>
              <div className="stepper">
                {[
                  "Connect your data",
                  "Describe a transformation",
                  "Explore your results",
                ].map((text, index) => (
                  <div
                    key={text}
                    className={`step ${steps[index] ? "done" : index === 0 || steps[index - 1] ? "current" : ""}`}
                  >
                    <span>
                      {steps[index] ? <Check size={14} /> : index + 1}
                    </span>
                    <strong>{text}</strong>
                    {index < 2 && <div className="step-line" />}
                  </div>
                ))}
              </div>
              <div className="workspace-grid">
                <section className="card source-card">
                  <div className="card-header">
                    <div>
                      <span className="section-kicker">01 / DATA SOURCE</span>
                      <h2>
                        <Database size={19} />
                        Connect to Amazon S3
                      </h2>
                    </div>
                    <span className="provider-icon">
                      <Cloud size={20} />
                    </span>
                  </div>
                  {!connection ? (
                    <form className="source-form" onSubmit={connect}>
                      <p className="helper">
                        Use a bucket you have permission to list and read.
                      </p>
                      {connections.length > 0 && (
                        <label>
                          Existing connection
                          <select
                            value=""
                            onChange={(e) => {
                              const item = connections.find(
                                (c) => c.id === e.target.value,
                              );
                              if (item) {
                                setConnection(item);
                                void loadFiles(item, "");
                              }
                            }}
                          >
                            <option value="">Choose a saved connection…</option>
                            {connections.map((item) => (
                              <option value={item.id} key={item.id}>
                                {item.bucket}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      <label>
                        Bucket name
                        <input
                          required
                          name="bucket"
                          placeholder="my-data-bucket"
                          autoComplete="off"
                          value={credentials.bucket}
                          onChange={(e) =>
                            setCredentials({
                              ...credentials,
                              bucket: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label>
                        AWS Access Key
                        <input
                          required
                          name="access_key"
                          placeholder="Enter your access key"
                          autoComplete="off"
                          spellCheck={false}
                          value={credentials.access_key}
                          onChange={(e) =>
                            setCredentials({
                              ...credentials,
                              access_key: e.target.value,
                            })
                          }
                        />
                      </label>
                      <label>
                        AWS Secret Key
                        <div className="input-icon">
                          <input
                            required
                            type="password"
                            name="secret_key"
                            placeholder="Enter your secret key"
                            autoComplete="new-password"
                            value={credentials.secret_key}
                            onChange={(e) =>
                              setCredentials({
                                ...credentials,
                                secret_key: e.target.value,
                              })
                            }
                          />
                          <LockKeyhole size={15} />
                        </div>
                      </label>
                      <label>
                        Bucket region
                        <input
                          required
                          list="regions"
                          value={credentials.region}
                          onChange={(e) =>
                            setCredentials({
                              ...credentials,
                              region: e.target.value,
                            })
                          }
                        />
                        <datalist id="regions">
                          {[
                            "us-east-1",
                            "us-west-2",
                            "ap-southeast-2",
                            "eu-west-1",
                            "ap-southeast-1",
                          ].map((r) => (
                            <option key={r} value={r} />
                          ))}
                        </datalist>
                      </label>
                      <button
                        type="button"
                        className="advanced-toggle"
                        aria-expanded={advanced}
                        onClick={() => setAdvanced(!advanced)}
                      >
                        Temporary AWS credentials <ChevronDown size={14} />
                      </button>
                      {advanced && (
                        <label>
                          Session token{" "}
                          <span className="optional">optional</span>
                          <input
                            type="password"
                            autoComplete="off"
                            value={credentials.session_token}
                            onChange={(e) =>
                              setCredentials({
                                ...credentials,
                                session_token: e.target.value,
                              })
                            }
                          />
                        </label>
                      )}
                      <button
                        className="button primary wide"
                        disabled={connecting || !ready}
                      >
                        {connecting ? (
                          <LoaderCircle size={16} className="spin" />
                        ) : (
                          <PlugZap size={16} />
                        )}
                        {connecting ? "Connecting securely…" : "Connect bucket"}
                        {!connecting && <ArrowRight size={16} />}
                      </button>
                      <div className="security-note">
                        <ShieldCheck size={14} />
                        <span>
                          Encrypted credentials. Read-only source access.
                        </span>
                      </div>
                    </form>
                  ) : (
                    <div className="connected-content">
                      <div className="bucket-connected">
                        <span className="bucket-icon">
                          <Cloud size={21} />
                        </span>
                        <div>
                          <strong>{connection.bucket}</strong>
                          <span>
                            <span className="tiny-dot" /> Connected ·{" "}
                            {connection.region}
                          </span>
                        </div>
                        <button
                          className="icon-button"
                          title="Disconnect this bucket"
                          disabled={processing}
                          onClick={() => {
                            void api
                              .disconnect(connection.id)
                              .then(() => {
                                setConnections((old) =>
                                  old.filter((c) => c.id !== connection.id),
                                );
                                setConnection(null);
                                setFiles([]);
                                setSelected(null);
                                setInspection(null);
                              })
                              .catch(report);
                          }}
                        >
                          <X size={16} />
                        </button>
                      </div>
                      <form
                        className="prefix-search"
                        onSubmit={(e) => {
                          e.preventDefault();
                          void loadFiles(connection, prefix);
                        }}
                      >
                        <Search size={15} />
                        <input
                          aria-label="S3 path prefix"
                          placeholder="Browse a path prefix…"
                          value={prefix}
                          onChange={(e) => setPrefix(e.target.value)}
                        />
                        <button
                          aria-label="Search files"
                          disabled={loadingFiles}
                        >
                          <ArrowRight size={16} />
                        </button>
                      </form>
                      <div className="file-list-heading">
                        <span>BUCKET FILES</span>
                        <span>{files.length} loaded</span>
                      </div>
                      <div className="file-list">
                        {!files.length ? (
                          <div className="compact-empty">
                            <FolderOpen size={24} />
                            <p>
                              {loadingFiles
                                ? "Loading files…"
                                : "No files in this path."}
                            </p>
                          </div>
                        ) : (
                          files.map((file) => (
                            <button
                              key={file.key}
                              className={`file-item ${selected?.key === file.key ? "chosen" : ""}`}
                              disabled={!file.supported || processing}
                              onClick={() => chooseFile(file)}
                              title={file.key}
                            >
                              <span
                                className={`file-icon ${file.key.toLowerCase().endsWith(".xlsx") ? "excel" : ""}`}
                              >
                                <FileSpreadsheet size={19} />
                              </span>
                              <span className="file-copy">
                                <strong>{filename(file.key)}</strong>
                                <small>
                                  {formatBytes(file.size)} ·{" "}
                                  {file.supported
                                    ? file.key
                                    : "Unsupported format"}
                                </small>
                              </span>
                              {selected?.key === file.key && (
                                <CheckCircle2 size={17} />
                              )}
                            </button>
                          ))
                        )}
                      </div>
                      {fileCursor && (
                        <button
                          className="text-button load-more"
                          disabled={loadingFiles}
                          onClick={() =>
                            void loadFiles(connection, prefix, fileCursor, true)
                          }
                        >
                          {loadingFiles ? "Loading…" : "Load more files"}
                        </button>
                      )}
                      {selected && (
                        <div className="file-options">
                          {selected.key.toLowerCase().endsWith(".csv") && (
                            <div className="form-row">
                              <label>
                                Delimiter
                                <select
                                  value={delimiter}
                                  disabled={processing}
                                  onChange={(e) => {
                                    setDelimiter(e.target.value);
                                    setInspection(null);
                                    setColumns([]);
                                  }}
                                >
                                  <option value=",">Comma (,)</option>
                                  <option value=";">Semicolon (;)</option>
                                  <option value={"\t"}>Tab</option>
                                  <option value="|">Pipe (|)</option>
                                </select>
                              </label>
                              <label>
                                Encoding
                                <select
                                  value={encoding}
                                  disabled={processing}
                                  onChange={(e) => {
                                    setEncoding(e.target.value);
                                    setInspection(null);
                                    setColumns([]);
                                  }}
                                >
                                  <option>UTF-8</option>
                                  <option>UTF-16</option>
                                  <option>ISO-8859-1</option>
                                </select>
                              </label>
                            </div>
                          )}
                          {!!inspection?.metadata?.sheets?.length && (
                            <label>
                              Worksheet
                              <select
                                value={sheet || inspection.metadata.sheet || ""}
                                disabled={processing}
                                onChange={(e) => {
                                  setSheet(e.target.value);
                                  setColumns([]);
                                  setInspection((old) =>
                                    old
                                      ? {
                                          ...old,
                                          metadata: {
                                            ...old.metadata,
                                            requires_sheet: true,
                                            columns: [],
                                            preview: [],
                                          },
                                        }
                                      : null,
                                  );
                                }}
                              >
                                <option value="" disabled>
                                  Select a worksheet…
                                </option>
                                {inspection.metadata.sheets.map((name) => (
                                  <option key={name}>{name}</option>
                                ))}
                              </select>
                            </label>
                          )}
                          <button
                            className="button secondary wide"
                            disabled={
                              submitting ||
                              processing ||
                              (!!inspection?.metadata?.requires_sheet && !sheet)
                            }
                            onClick={() => void inspectFile()}
                          >
                            {active(inspection) ? (
                              <LoaderCircle size={15} className="spin" />
                            ) : (
                              <Search size={15} />
                            )}
                            {active(inspection)
                              ? "Inspecting file…"
                              : schema.length
                                ? "Refresh preview"
                                : "Inspect selected file"}
                          </button>
                          {inspection?.status === "FAILED" && (
                            <p className="inline-error">
                              {inspection.error?.message}
                            </p>
                          )}
                          {active(inspection) && (
                            <button
                              className="text-button"
                              onClick={() => void cancel(inspection!)}
                            >
                              Cancel inspection
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="card-footnote">
                    <FileSpreadsheet size={14} />
                    CSV and Excel (.xlsx)
                    <span>Source files stay unchanged</span>
                  </div>
                </section>

                <section className="card transform-card">
                  <div className="card-header">
                    <div>
                      <span className="section-kicker">
                        02 / TRANSFORMATION
                      </span>
                      <h2>
                        <Sparkles size={19} />
                        Describe it. Transform it.
                      </h2>
                    </div>
                    <span className="ai-label">AI ASSISTED</span>
                  </div>
                  <form onSubmit={submit}>
                    <fieldset disabled={processing || submitting}>
                      <div className="operation-tabs">
                        {operations.map((item) => (
                          <button
                            type="button"
                            key={item.id}
                            className={
                              operation === item.id
                                ? "operation active"
                                : "operation"
                            }
                            onClick={() => {
                              setOperation(item.id);
                              setPrompt("");
                              if (item.id === "regex_extract")
                                setColumns((old) => old.slice(0, 1));
                              submitKey.current = crypto.randomUUID();
                            }}
                          >
                            <item.icon size={17} />
                            <span>{item.title}</span>
                          </button>
                        ))}
                      </div>
                      <div className="transformation-form">
                        <label>
                          What would you like to{" "}
                          {operation === "normalize"
                            ? "standardize"
                            : operation === "regex_extract"
                              ? "extract"
                              : "find"}
                          ?
                          <textarea
                            required
                            minLength={3}
                            maxLength={4000}
                            value={prompt}
                            onChange={(e) => {
                              setPrompt(e.target.value);
                              submitKey.current = crypto.randomUUID();
                            }}
                            placeholder={
                              operation === "regex_replace"
                                ? "e.g. Find all email addresses in the selected columns"
                                : operation === "regex_extract"
                                  ? "e.g. Extract the first order ID starting with ORD-"
                                  : "e.g. Trim extra whitespace and convert names to lowercase"
                            }
                          />
                          <span className="textarea-caption">
                            <Sparkles size={12} />
                            Describe the rule in your own words
                            <span>{prompt.length}/4000</span>
                          </span>
                        </label>
                        <div className="suggestions">
                          <span>Try</span>
                          {suggestions[operation].map((item) => (
                            <button
                              type="button"
                              key={item.label}
                              onClick={() => {
                                setPrompt(item.text);
                                submitKey.current = crypto.randomUUID();
                              }}
                            >
                              {item.label}
                              <ArrowUpRight size={11} />
                            </button>
                          ))}
                        </div>
                        <div className="field-heading">
                          <label>
                            Target{" "}
                            {operation === "regex_extract"
                              ? "column"
                              : "columns"}
                          </label>
                          {schema.length > 0 &&
                            operation !== "regex_extract" && (
                              <button
                                type="button"
                                className="text-button"
                                onClick={() =>
                                  setColumns(
                                    columns.length === schema.length
                                      ? []
                                      : schema.map((c) => c.name),
                                  )
                                }
                              >
                                {columns.length === schema.length
                                  ? "Clear all"
                                  : "Select all"}
                              </button>
                            )}
                        </div>
                        {!schema.length ? (
                          <div className="column-placeholder">
                            <Database size={16} />
                            Connect and inspect a file to choose columns.
                          </div>
                        ) : (
                          <div className="column-options">
                            {schema.map((col) => (
                              <label
                                className={`column-choice ${columns.includes(col.name) ? "checked" : ""}`}
                                key={col.name}
                              >
                                <input
                                  type={
                                    operation === "regex_extract"
                                      ? "radio"
                                      : "checkbox"
                                  }
                                  name="target-columns"
                                  checked={columns.includes(col.name)}
                                  onChange={() =>
                                    setColumns((old) =>
                                      operation === "regex_extract"
                                        ? [col.name]
                                        : old.includes(col.name)
                                          ? old.filter(
                                              (name) => name !== col.name,
                                            )
                                          : [...old, col.name],
                                    )
                                  }
                                />
                                <span className="type-mark">Aa</span>
                                {col.name}
                              </label>
                            ))}
                          </div>
                        )}
                        {operation === "regex_replace" && (
                          <label>
                            Replace with{" "}
                            <span className="optional">
                              leave empty to remove matches
                            </span>
                            <input
                              maxLength={4000}
                              value={replacement}
                              onChange={(e) => {
                                setReplacement(e.target.value);
                                submitKey.current = crypto.randomUUID();
                              }}
                              placeholder="Replacement text"
                            />
                          </label>
                        )}
                        {operation === "regex_extract" && (
                          <label>
                            New column name
                            <input
                              required
                              pattern="[\w][\w .-]{0,127}"
                              value={newColumn}
                              onChange={(e) => setNewColumn(e.target.value)}
                            />
                            <span className="helper">
                              The first match becomes a new column. Original
                              data is preserved.
                            </span>
                          </label>
                        )}
                        {operation === "normalize" && (
                          <div className="normalization-note">
                            <CheckCircle2 size={15} />
                            Supports trimming, whitespace cleanup, lowercase and
                            uppercase.
                          </div>
                        )}
                        <div className="run-summary">
                          <div>
                            <span className="run-icon">
                              <Layers3 size={17} />
                            </span>
                            <div>
                              <strong>
                                {selected
                                  ? filename(selected.key)
                                  : "Ready when you are"}
                              </strong>
                              <span>
                                {columns.length
                                  ? `${columns.length} target column${columns.length > 1 ? "s" : ""} · ${transformation.title}`
                                  : "Select a source file and target columns"}
                              </span>
                            </div>
                          </div>
                          <button
                            className="button primary"
                            disabled={
                              !ready ||
                              !boot?.llm_configured ||
                              !schema.length ||
                              !columns.length ||
                              !prompt.trim() ||
                              processing ||
                              submitting
                            }
                          >
                            {submitting ? (
                              <LoaderCircle size={15} className="spin" />
                            ) : (
                              <Play size={14} fill="currentColor" />
                            )}
                            {submitting ? "Submitting…" : "Run transformation"}
                          </button>
                        </div>
                        <p className="run-note">
                          <ShieldCheck size={13} />
                          Rules are validated before they run. Your job
                          continues in the background.
                        </p>
                      </div>
                    </fieldset>
                  </form>
                </section>
              </div>

              {current && (
                <section className="card job-card" aria-live="polite">
                  <div className="job-header">
                    <div
                      className={`job-symbol ${current.status.toLowerCase()}`}
                    >
                      {active(current) ? (
                        <LoaderCircle size={21} className="spin" />
                      ) : current.status === "SUCCESS" ? (
                        <CheckCircle2 size={22} />
                      ) : (
                        <Square size={20} />
                      )}
                    </div>
                    <div className="job-title">
                      <h3>{stageLabels[current.stage] || current.stage}</h3>
                      <span>
                        {filename(current.source_key)} · Job{" "}
                        {current.id.slice(0, 8)} · Attempt{" "}
                        {current.attempt || 1}
                        {current.status === "SUCCESS" &&
                        job?.metadata?.cache_hit
                          ? " · Cached rule"
                          : ""}
                      </span>
                    </div>
                    <Status job={current} />
                    {active(current) && (
                      <button
                        className="button secondary small"
                        disabled={current.cancel_requested}
                        onClick={() => void cancel(current)}
                      >
                        <Square size={12} />
                        {current.cancel_requested
                          ? "Cancelling…"
                          : "Cancel job"}
                      </button>
                    )}
                  </div>
                  {active(current) && (
                    <>
                      <div className="progress-track">
                        <div style={{ width: `${current.progress}%` }} />
                      </div>
                      <div className="progress-caption">
                        <span>Stage-based estimate · {current.progress}%</span>
                        <span>
                          You can leave this page and return to Activity.
                        </span>
                      </div>
                    </>
                  )}
                  {current.error && (
                    <div className="job-error">
                      <strong>{current.error.code}</strong>
                      <p>{current.error.message}</p>
                    </div>
                  )}
                  {job?.plan?.explanation && (
                    <div className="rule-preview">
                      <div>
                        <Code2 size={15} />
                        <strong>Validated rule</strong>
                        {job.metadata?.cache_hit && (
                          <span className="subtle-badge">CACHE HIT</span>
                        )}
                        <button
                          className="icon-button"
                          aria-label="Copy validated rule"
                          onClick={() => {
                            void navigator.clipboard
                              .writeText(
                                job.plan?.pattern ||
                                  job.plan?.steps.join(" → ") ||
                                  "",
                              )
                              .then(() => {
                                setCopied(true);
                                setTimeout(() => setCopied(false), 1500);
                              })
                              .catch(report);
                          }}
                        >
                          {copied ? <Check size={15} /> : <Copy size={15} />}
                        </button>
                      </div>
                      <code>
                        {job.plan.pattern || job.plan.steps.join(" → ")}
                      </code>
                      <p>{job.plan.explanation}</p>
                    </div>
                  )}
                </section>
              )}

              <section className="card results-card">
                <div className="card-header">
                  <div>
                    <span className="section-kicker">03 / YOUR DATA</span>
                    <h2>
                      <FileSpreadsheet size={19} />
                      {page ? "Processed results" : "Data preview"}
                      {tableColumns.length > 0 && (
                        <span className="subtle-badge">
                          {page
                            ? `${page.total_rows.toLocaleString()} ROWS`
                            : "FIRST 100 ROWS"}
                        </span>
                      )}
                    </h2>
                  </div>
                  {page && (
                    <span className="results-success">
                      <CheckCircle2 size={15} />
                      {changed.toLocaleString()} cells changed
                    </span>
                  )}
                </div>
                {!tableColumns.length ? (
                  <div className="empty-state results-empty">
                    <div className="empty-grid">
                      <FileSpreadsheet size={26} />
                      <span />
                      <span />
                      <span />
                    </div>
                    <h3>A clearer view of your data starts here.</h3>
                    <p>
                      Inspect a file to preview its columns.
                      <br />
                      Your processed results will appear here when the job is
                      complete.
                    </p>
                    <div className="empty-features">
                      <span>
                        <Check size={12} />
                        Safe previews
                      </span>
                      <span>
                        <Check size={12} />
                        Paginated results
                      </span>
                      <span>
                        <Check size={12} />
                        Millions of rows
                      </span>
                    </div>
                  </div>
                ) : (
                  <>
                    {tableRows.length ? (
                      <DataTable
                        rows={tableRows}
                        columns={tableColumns}
                        selected={columns}
                      />
                    ) : (
                      <div className="compact-empty">
                        <Database size={25} />
                        <p>This dataset has columns but no data rows.</p>
                      </div>
                    )}
                    <div className="pagination">
                      <span>
                        {page
                          ? `Showing ${page.total_rows ? page.offset + 1 : 0}–${page.offset + page.returned_rows} of ${page.total_rows.toLocaleString()} rows`
                          : `${tableRows.length} sample rows · Preview is not the full dataset`}
                      </span>
                      {page && (
                        <div>
                          <label>
                            Rows
                            <select
                              aria-label="Rows per page"
                              value={pageSize}
                              disabled={loadingPage}
                              onChange={(e) =>
                                setPageSize(Number(e.target.value))
                              }
                            >
                              <option value={25}>25</option>
                              <option value={100}>100</option>
                              <option value={500}>500</option>
                            </select>
                          </label>
                          <button
                            className="icon-button"
                            aria-label="Previous result page"
                            disabled={loadingPage || !pageNumber}
                            onClick={() => {
                              if (job)
                                void loadPage(
                                  job,
                                  cursors[pageNumber - 1],
                                  pageNumber - 1,
                                );
                            }}
                          >
                            <ChevronLeft size={17} />
                          </button>
                          <span>
                            {loadingPage ? (
                              <LoaderCircle size={15} className="spin" />
                            ) : (
                              `Page ${pageNumber + 1}`
                            )}
                          </span>
                          <button
                            className="icon-button"
                            aria-label="Next result page"
                            disabled={loadingPage || !page.next_cursor}
                            onClick={() => {
                              if (job && page.next_cursor) {
                                const next = [
                                  ...cursors.slice(0, pageNumber + 1),
                                  page.next_cursor,
                                ];
                                setCursors(next);
                                void loadPage(
                                  job,
                                  page.next_cursor,
                                  pageNumber + 1,
                                );
                              }
                            }}
                          >
                            <ChevronRight size={17} />
                          </button>
                        </div>
                      )}
                    </div>
                    {page && job?.result_expires_at && (
                      <div className="retention-note">
                        <Clock3 size={12} />
                        Results available until{" "}
                        {new Date(job.result_expires_at).toLocaleString()}.
                        Original S3 data is unchanged.
                      </div>
                    )}
                  </>
                )}
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>
              <Layers3 size={13} />
              PatternForge
            </span>
            <span>
              From a simple instruction to a meaningful transformation.
            </span>
            <button className="text-button" onClick={() => setGuide(true)}>
              Need a hand? <ArrowUpRight size={13} />
            </button>
          </footer>
        </div>
      </main>
      {guide && (
        <div className="modal-backdrop" onClick={() => setGuide(false)}>
          <section
            className="guide-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="guide-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button modal-close"
              aria-label="Close guide"
              onClick={() => setGuide(false)}
            >
              <X size={20} />
            </button>
            <span className="section-kicker">A LITTLE GUIDANCE</span>
            <h2 id="guide-title">From your bucket to better data.</h2>
            <p>Three steps. Your original files are always preserved.</p>
            <ol>
              <li>
                <strong>Connect your source</strong>
                <p>
                  Enter credentials with permission to list your bucket and read
                  its objects. Temporary credentials also need a session token.
                  Choose CSV or .xlsx and inspect it.
                </p>
              </li>
              <li>
                <strong>Describe the change</strong>
                <p>
                  Select the columns, choose replace, extract or standardize,
                  and describe your rule. For replacement, an empty value
                  removes matches. Extraction creates a new column.
                </p>
              </li>
              <li>
                <strong>Follow your job</strong>
                <p>
                  Processing runs in the background. View status in Activity,
                  cancel unneeded jobs, and browse the result a page at a time.
                  Zero matches is a successful result.
                </p>
              </li>
            </ol>
            <div className="guide-privacy">
              <ShieldCheck size={20} />
              <div>
                <strong>A private workspace</strong>
                <p>
                  Your session can only see its own jobs. Credentials are
                  encrypted, never sent to the language model, and expire
                  automatically. Results are kept for{" "}
                  {boot?.limits.result_ttl_hours || 24} hours.
                </p>
              </div>
            </div>
            <details>
              <summary>
                <Terminal size={15} />
                Administrator setup
              </summary>
              <p>
                Run the project bootstrap, configure LLM_API_KEY and LLM_MODEL
                in the private .env file, then start Docker Compose. For local
                development, use the VS Code tasks in the repository. No model
                output is fabricated when configuration is missing.
              </p>
              <p>
                CSV supports up to{" "}
                {formatBytes(boot?.limits.max_file_bytes || 2 * 1024 ** 3)};
                Excel up to{" "}
                {formatBytes(boot?.limits.max_excel_bytes || 100 * 1024 ** 2)}.
                Column names must be unique. See README for deployment and
                permissions.
              </p>
            </details>
            <button
              className="button primary wide"
              onClick={() => setGuide(false)}
            >
              Back to workspace <ArrowRight size={15} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
