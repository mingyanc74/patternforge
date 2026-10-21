import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Braces,
  Check,
  ChevronLeft,
  ChevronRight,
  Circle,
  CircleAlert,
  CircleHelp,
  Clock3,
  Copy,
  Database,
  FileSpreadsheet,
  FolderClosed,
  History,
  Info,
  LoaderCircle,
  LockKeyhole,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Square,
  Table2,
  X,
} from "lucide-react";
import { api, RequestError } from "./api";
import type {
  Bootstrap,
  Connection,
  Job,
  Operation,
  ResultPage,
  SourceFile,
} from "./api";
import {
  active,
  dateLabel,
  durationLabel,
  filename,
  formatBytes,
  operationLabel,
  resultExpired,
  stageLabels,
} from "./utils";
import { DataTable } from "./components/DataTable";
import { JobsHistory } from "./components/JobsHistory";
import { Modal } from "./components/Modal";
import { Status } from "./components/Status";
import { Datasets } from "./components/Datasets";

type Screen =
  | "connection"
  | "files"
  | "editor"
  | "job"
  | "results"
  | "history"
  | "datasets";
type Dialog = "help" | "review" | "cancel" | "disconnect" | "discard" | null;
const stages = [
  "VALIDATING",
  "GENERATING_PLAN",
  "VALIDATING_RULE",
  "READING",
  "TRANSFORMING",
  "WRITING",
];
const examples: Record<Operation, string> = {
  regex_replace: "Find email addresses",
  regex_extract: "Extract order IDs beginning with ORD- followed by digits",
  normalize:
    "Trim spaces, collapse repeated whitespace, then convert to lowercase",
};

function useJobPolling(
  job: Job | null,
  update: (job: Job) => void,
  onError: (message: string) => void,
) {
  useEffect(() => {
    if (!active(job)) return;
    let stopped = false,
      failures = 0;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await api.job(job!.id);
        if (stopped) return;
        update(next);
        failures = 0;
        onError("");
        if (active(next)) timer = setTimeout(poll, 2000);
      } catch (error) {
        if (stopped) return;
        onError(
          error instanceof Error
            ? error.message
            : "Connection interrupted. Your job continues on the server.",
        );
        timer = setTimeout(poll, Math.min(15000, 2000 * 2 ** ++failures));
      }
    }
    timer = setTimeout(poll, 1000);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status, update, onError]);
}

export default function App() {
  const [screen, setScreen] = useState<Screen>("history");
  const [boot, setBoot] = useState<Bootstrap | null>(null),
    [services, setServices] = useState<Record<string, boolean>>({});
  const [error, setError] = useState(""),
    [network, setNetwork] = useState(""),
    [initializing, setInitializing] = useState(true);
  const [connections, setConnections] = useState<Connection[]>([]),
    [connection, setConnection] = useState<Connection | null>(null);
  const [accessPassword, setAccessPassword] = useState(""),
    [unlocking, setUnlocking] = useState(false);
  const [credentials, setCredentials] = useState({
    access_key: "",
    secret_key: "",
    session_token: "",
    bucket: "",
    region: "us-east-1",
  });
  const [connecting, setConnecting] = useState(false),
    [showSecret, setShowSecret] = useState(false);
  const [files, setFiles] = useState<SourceFile[]>([]),
    [prefix, setPrefix] = useState("");
  const [fileCursor, setFileCursor] = useState<string | null>(null),
    [loadingFiles, setLoadingFiles] = useState(false);
  const [selected, setSelected] = useState<SourceFile | null>(null),
    [sheet, setSheet] = useState(""),
    [sheets, setSheets] = useState<string[]>([]);
  const [delimiter, setDelimiter] = useState(","),
    [encoding, setEncoding] = useState("UTF-8");
  const [inspection, setInspection] = useState<Job | null>(null),
    [job, setJob] = useState<Job | null>(null);
  const [operation, setOperation] = useState<Operation>("regex_replace"),
    [columns, setColumns] = useState<string[]>([]);
  const [prompt, setPrompt] = useState(""),
    [replacement, setReplacement] = useState(""),
    [removeMatches, setRemoveMatches] = useState(false),
    [newColumn, setNewColumn] = useState("");
  const [submitting, setSubmitting] = useState(false),
    [jobCount, setJobCount] = useState(0);
  const [page, setPage] = useState<ResultPage | null>(null),
    [cursors, setCursors] = useState<string[]>([""]),
    [pageNumber, setPageNumber] = useState(0),
    [pageSize, setPageSize] = useState(100),
    [loadingPage, setLoadingPage] = useState(false);
  const [dataView, setDataView] = useState<"result" | "original">("result");
  const [pendingReuse, setPendingReuse] = useState<Job | null>(null),
    [reusedFrom, setReusedFrom] = useState("");
  const [dialog, setDialog] = useState<Dialog>(null),
    [cancelTarget, setCancelTarget] = useState<Job | null>(null),
    [toast, setToast] = useState("");
  const submitKey = useRef(crypto.randomUUID()),
    pageSequence = useRef(0),
    fileSequence = useRef(0),
    restoreSequence = useRef(0);
  const pendingAction = useRef<(() => void) | null>(null);
  const currentJobId = useRef(job?.id);
  currentJobId.current = job?.id;
  const screenRef = useRef(screen);
  screenRef.current = screen;
  const schema =
    inspection?.status === "SUCCESS" && !inspection.metadata?.requires_sheet
      ? inspection.metadata?.columns || []
      : [];
  const dirty = !!(prompt || columns.length || replacement || newColumn);
  const processing = active(inspection) || active(job);
  function toggleColumn(name: string) {
    if (processing) return;
    setColumns((old) =>
      operation === "regex_extract"
        ? [name]
        : old.includes(name)
          ? old.filter((column) => column !== name)
          : [...old, name].slice(0, 50),
    );
  }
  const report = useCallback((value: unknown) => {
    if (value instanceof RequestError && value.code === "ACCESS_REQUIRED") {
      setBoot((old) => (old ? { ...old, access_required: true } : old));
      setCredentials((old) => ({
        ...old,
        access_key: "",
        secret_key: "",
        session_token: "",
      }));
    }
    setError(
      value instanceof Error
        ? value.message
        : "Something went wrong. Please retry.",
    );
  }, []);
  const go = useCallback((next: Screen) => {
    setScreen(next);
    setError("");
  }, []);
  useJobPolling(inspection, setInspection, setNetwork);
  useJobPolling(job, setJob, setNetwork);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(timer);
  }, [toast]);
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
    removeMatches,
    newColumn,
  ]);

  const loadFiles = useCallback(
    async (item: Connection, path: string, cursor = "", append = false) => {
      const sequence = ++fileSequence.current;
      setLoadingFiles(true);
      try {
        const result = await api.files(item.id, path, cursor);
        if (sequence !== fileSequence.current) return;
        setFiles((old) => (append ? [...old, ...result.files] : result.files));
        setFileCursor(result.next_cursor);
      } catch (value) {
        if (sequence === fileSequence.current) report(value);
      } finally {
        if (sequence === fileSequence.current) setLoadingFiles(false);
      }
    },
    [report],
  );

  const openJob = useCallback(
    async (item: Job | string) => {
      const sequence = ++restoreSequence.current;
      setError("");
      try {
        const next = await api.job(typeof item === "string" ? item : item.id);
        if (sequence !== restoreSequence.current) return;
        if (next.kind === "inspect") {
          setInspection(next);
          setScreen("files");
          return;
        }
        setJob(next);
        setPage(null);
        setScreen("job");
        setDataView("result");
        setInspection(null);
        window.history.replaceState(null, "", "#job=" + next.id);
        if (next.config?.inspection_id) {
          const source = await api.job(String(next.config.inspection_id));
          if (sequence === restoreSequence.current) setInspection(source);
        }
      } catch (value) {
        if (sequence === restoreSequence.current) report(value);
      }
    },
    [report],
  );

  const initialize = useCallback(async () => {
    setInitializing(true);
    setError("");
    try {
      const config = await api.bootstrap();
      setBoot(config);
      if (config.access_required) return;
      const [saved, jobs, health] = await Promise.all([
        api.connections(),
        api.jobs({ kind: "transform", limit: 1 }),
        api.health(),
      ]);
      setConnections(saved.connections);
      setConnection(saved.connections[0] || null);
      setJobCount(jobs.total);
      setServices(health.services);
      const match = location.hash.match(/^#job=([a-f0-9-]{36})$/i);
      if (match) await openJob(match[1]);
    } catch (value) {
      report(value);
    } finally {
      setInitializing(false);
    }
  }, [openJob, report]);
  useEffect(() => {
    void initialize();
  }, [initialize]);
  useEffect(() => {
    if (inspection?.status !== "SUCCESS") return;
    if (inspection.metadata?.sheets) setSheets(inspection.metadata.sheets);
    if (
      !inspection.metadata?.requires_sheet &&
      inspection.metadata?.columns?.length &&
      screenRef.current === "files"
    )
      setScreen("editor");
  }, [inspection?.id, inspection?.status]);

  const loadPage = useCallback(
    async (current: Job, cursor: string, index: number) => {
      const sequence = ++pageSequence.current;
      setLoadingPage(true);
      setError("");
      try {
        const next = await api.results(current.id, cursor, pageSize);
        if (
          sequence === pageSequence.current &&
          currentJobId.current === current.id
        ) {
          setPage(next);
          setPageNumber(index);
        }
      } catch (value) {
        if (sequence === pageSequence.current) report(value);
      } finally {
        if (sequence === pageSequence.current) setLoadingPage(false);
      }
    },
    [pageSize, report],
  );
  useEffect(() => {
    if (
      screen === "results" &&
      job?.status === "SUCCESS" &&
      !resultExpired(job)
    ) {
      setCursors([""]);
      setPage(null);
      void loadPage(job, "", 0);
    }
  }, [screen, job?.id, job?.status, pageSize, loadPage]);

  function clearDraft() {
    setInspection(null);
    setSelected(null);
    setColumns([]);
    setPrompt("");
    setReplacement("");
    setRemoveMatches(false);
    setNewColumn("");
    setReusedFrom("");
    setPendingReuse(null);
    setSheet("");
    setSheets([]);
  }
  function confirmDraft(action: () => void) {
    if (dirty && !job) {
      pendingAction.current = action;
      setDialog("discard");
    } else action();
  }
  function newJob() {
    confirmDraft(() => {
      clearDraft();
      setJob(null);
      setPage(null);
      window.history.replaceState(null, "", location.pathname);
      if (
        connection &&
        new Date(connection.expires_at).getTime() > Date.now()
      ) {
        go("files");
        void loadFiles(connection, prefix);
      } else go(inspection?.dataset_available ? "datasets" : "connection");
    });
  }
  function prepare() {
    if (job) {
      if (active(job)) go("job");
      else newJob();
      return;
    }
    const connected =
      connection && new Date(connection.expires_at).getTime() > Date.now();
    go(schema.length ? "editor" : connected ? "files" : "connection");
    if (connection && connected && !schema.length && !files.length)
      void loadFiles(connection, prefix);
  }
  function resetInspection() {
    setInspection(null);
    setColumns([]);
  }
  function chooseFile(file: SourceFile) {
    if (job) {
      setJob(null);
      setPage(null);
      setPrompt("");
      setReplacement("");
      setNewColumn("");
      setReusedFrom("");
    }
    setSelected(file);
    resetInspection();
    setSheet("");
    setSheets([]);
    setError("");
    if (pendingReuse && pendingReuse.source_key !== file.key)
      setPendingReuse(null);
  }
  function openDataset(item: Job) {
    clearDraft();
    setJob(null);
    setPage(null);
    setInspection(item);
    setConnection(
      connections.find((value) => value.id === item.connection_id) || {
        id: item.connection_id,
        bucket: item.bucket || "",
        region: item.region || "",
        source_type: item.source_type,
        expires_at: item.created_at,
      },
    );
    setSelected({
      key: item.source_key,
      size: 0,
      supported: true,
      modified: item.created_at,
    });
    setSheet(item.metadata?.sheet || "");
    setDelimiter(String(item.config?.delimiter || ","));
    setEncoding(String(item.config?.encoding || "UTF-8"));
    window.history.replaceState(null, "", location.pathname);
    go("editor");
  }
  async function applyReuse(item: Job) {
    const config = item.config || {};
    setOperation(
      (config.operation as Operation) || item.operation || "regex_replace",
    );
    setPrompt(String(config.prompt || ""));
    setReplacement(String(config.replacement ?? ""));
    setRemoveMatches(config.replacement === "");
    setNewColumn(String(config.new_column || ""));
    setColumns([]);
    setReusedFrom(item.id);
    setJob(null);
    setPage(null);
    setSheet(String(config.sheet || ""));
    setDelimiter(String(config.delimiter || ","));
    setEncoding(String(config.encoding || "UTF-8"));
    setInspection(null);
    setSheets([]);
    setPendingReuse(item);
    if (config.inspection_id) {
      try {
        const imported = await api.job(String(config.inspection_id));
        if (imported.dataset_available) {
          setInspection(imported);
          setConnection(
            connections.find(
              (value) => value.id === imported.connection_id,
            ) || {
              id: imported.connection_id,
              bucket: imported.bucket || "",
              region: imported.region || "",
              source_type: imported.source_type,
              expires_at: imported.created_at,
            },
          );
          setSelected({
            key: imported.source_key,
            size: 0,
            supported: true,
            modified: imported.created_at,
          });
          window.history.replaceState(null, "", location.pathname);
          go("editor");
          return;
        }
      } catch (value) {
        report(value);
        return;
      }
    }
    const linked = connections.find(
      (value) =>
        value.id === item.connection_id ||
        (value.bucket === item.bucket &&
          value.region === item.region &&
          (value.source_type || "amazon_s3") ===
            (item.source_type || "amazon_s3")),
    );
    setConnection(linked || null);
    setSelected({
      key: item.source_key,
      size: 0,
      supported: true,
      modified: item.created_at,
    });
    const folder = item.source_key.includes("/")
      ? item.source_key.slice(0, item.source_key.lastIndexOf("/") + 1)
      : "";
    setPrefix(folder);
    window.history.replaceState(null, "", location.pathname);
    if (linked) {
      go("files");
      void loadFiles(linked, folder);
    } else {
      setCredentials((old) => ({
        ...old,
        bucket: item.bucket || "",
        region: item.region || "us-east-1",
        access_key: "",
        secret_key: "",
        session_token: "",
      }));
      go("connection");
    }
  }
  function requestReuse(item: Job) {
    confirmDraft(() => {
      void api.job(item.id).then(applyReuse).catch(report);
    });
  }
  useEffect(() => {
    if (!pendingReuse || !schema.length) return;
    const wanted = (pendingReuse.config?.target_columns as string[]) || [],
      available = schema.map((column) => column.name);
    setColumns(
      wanted
        .filter((name) => available.includes(name))
        .slice(0, operation === "regex_extract" ? 1 : 50),
    );
    if (wanted.some((name) => !available.includes(name)))
      setError(
        "Some reused columns no longer exist. Select columns from the new preview.",
      );
    setPendingReuse(null);
  }, [inspection?.id, inspection?.status]);

  async function connect(event: React.FormEvent) {
    event.preventDefault();
    setConnecting(true);
    setError("");
    try {
      const next = await api.connect(credentials);
      setConnection(next);
      setConnections((old) => [next, ...old]);
      setCredentials((old) => ({
        ...old,
        access_key: "",
        secret_key: "",
        session_token: "",
      }));
      setShowSecret(false);
      const matching =
        pendingReuse?.bucket === next.bucket &&
        pendingReuse?.region === next.region &&
        (pendingReuse?.source_type || "amazon_s3") ===
          (next.source_type || "amazon_s3");
      if (!matching) {
        clearDraft();
        setPrefix("");
      }
      go("files");
      await loadFiles(next, matching ? prefix : "");
    } catch (value) {
      report(value);
    } finally {
      setConnecting(false);
    }
  }
  async function connectSample() {
    setConnecting(true);
    setError("");
    try {
      const next = await api.connectSample();
      const matching =
        pendingReuse?.source_type === "sample" &&
        pendingReuse.bucket === next.bucket;
      if (!matching) clearDraft();
      setConnection(next);
      setConnections((old) => [
        next,
        ...old.filter((item) => item.id !== next.id),
      ]);
      setCredentials((old) => ({
        ...old,
        access_key: "",
        secret_key: "",
        session_token: "",
      }));
      setShowSecret(false);
      if (!matching) setPrefix("");
      go("files");
      await loadFiles(next, matching ? prefix : "");
    } catch (value) {
      report(value);
    } finally {
      setConnecting(false);
    }
  }
  async function inspectFile() {
    if (!connection || !selected) return;
    setSubmitting(true);
    setError("");
    setColumns([]);
    try {
      setInspection(
        await api.inspect({
          connection_id: connection.id,
          source_key: selected.key,
          sheet,
          delimiter,
          encoding,
        }),
      );
    } catch (value) {
      report(value);
    } finally {
      setSubmitting(false);
    }
  }
  function validateDraft() {
    if (!schema.length)
      return "Preview the selected file before configuring a job.";
    if (!columns.length) return "Choose at least one target column.";
    if (prompt.trim().length < 3)
      return "Describe the pattern or formatting in at least three characters.";
    if (operation === "regex_replace" && !removeMatches && replacement === "")
      return "Enter replacement text, or select ‘Remove matched text instead’.";
    if (
      operation === "regex_extract" &&
      (!/^[\p{L}\p{N}_][\p{L}\p{N}_ .-]{0,127}$/u.test(newColumn) ||
        schema.some((c) => c.name.toLowerCase() === newColumn.toLowerCase()))
    )
      return "Choose a unique new column name using letters, digits, spaces, dots, dashes or underscores.";
    return "";
  }
  async function submit() {
    const issue = validateDraft();
    if (issue) {
      setError(issue);
      setDialog(null);
      return;
    }
    if (!connection || !selected || !inspection) return;
    setSubmitting(true);
    setError("");
    try {
      const next = await api.createJob(
        {
          connection_id: connection.id,
          source_key: selected.key,
          inspection_id: inspection.id,
          sheet: inspection.metadata?.sheet || sheet,
          delimiter,
          encoding,
          operation,
          prompt,
          target_columns: columns,
          ...(operation === "regex_replace"
            ? { replacement: removeMatches ? "" : replacement }
            : {}),
          ...(operation === "regex_extract" ? { new_column: newColumn } : {}),
        },
        submitKey.current,
      );
      setJob(next);
      setJobCount((count) => count + 1);
      setPage(null);
      setDataView("result");
      setDialog(null);
      go("job");
      window.history.replaceState(null, "", "#job=" + next.id);
      submitKey.current = crypto.randomUUID();
    } catch (value) {
      report(value);
      if (value instanceof RequestError && value.code !== "NETWORK_ERROR")
        submitKey.current = crypto.randomUUID();
    } finally {
      setSubmitting(false);
    }
  }
  async function cancel() {
    if (!cancelTarget) return;
    setSubmitting(true);
    try {
      const next = await api.cancel(cancelTarget.id);
      next.kind === "inspect" ? setInspection(next) : setJob(next);
      setDialog(null);
    } catch (value) {
      report(value);
    } finally {
      setSubmitting(false);
    }
  }
  async function disconnect() {
    if (!connection) return;
    setSubmitting(true);
    try {
      await api.disconnect(connection.id);
      setConnections((old) => old.filter((item) => item.id !== connection.id));
      setConnection(null);
      clearDraft();
      setFiles([]);
      setJob(null);
      setDialog(null);
      go("connection");
    } catch (value) {
      report(value);
    } finally {
      setSubmitting(false);
    }
  }
  function requestCancel(item: Job) {
    setCancelTarget(item);
    setDialog("cancel");
  }
  const phase = ["connection", "files", "editor", "job", "results"].indexOf(
    screen,
  );
  const canOpen = (next: Screen) =>
    next === "connection" ||
    (next === "files"
      ? !!connection
      : next === "editor"
        ? !!schema.length && !!selected && !job
        : next === "job"
          ? !!job
          : next === "results"
            ? job?.status === "SUCCESS"
            : true);
  const titles: Record<Screen, string> = {
    datasets: "Imported datasets",
    history: "Jobs",
    connection: "Connect your data",
    files: "Select a file",
    editor: "Configure transformation",
    job: "Job details",
    results: job && resultExpired(job) ? "Results expired" : "Results",
  };
  const description =
    screen === "datasets"
      ? "Use previously imported data without reconnecting to S3."
      : screen === "history"
        ? "Review past jobs and reuse a configuration."
        : screen === "connection"
          ? "Choose the S3 bucket that contains your CSV or Excel file."
          : screen === "files"
            ? (connection?.source_type === "sample" ? "sample://" : "s3://") +
              (connection?.bucket || "") +
              " · CSV and Excel (.xlsx)"
            : screen === "results"
              ? job?.source_key
              : "";
  const changed = Object.values(job?.metadata?.changed_cells || {}).reduce(
    (sum, value) => sum + value,
    0,
  );
  const jobConfig = job?.config || {},
    inputPreview = inspection?.metadata?.preview || [];
  const noServices =
    boot &&
    (!services.queue ||
      !services.worker ||
      !services.spark ||
      !boot.llm_configured);
  if (boot?.access_required)
    return (
      <main className="access-screen">
        <section className="access-story" aria-label="About Rulecraft">
          <div className="access-brand">
            <span className="brand-mark">
              <Braces />
            </span>
            Rulecraft
          </div>
          <div className="access-story-content">
            <h1>
              Good data starts
              <br />
              with a clear rule.
            </h1>
            <p>
              Turn your CSV and Excel files into usable data. Describe the
              change, review the result, keep the original.
            </p>
            <div className="rule-example">
              <div className="rule-example-head">
                <span>Transformation example</span>
                <span className="format-tag">Find &amp; replace</span>
              </div>
              <p className="example-instruction">“Find email addresses”</p>
              <div className="rule-example-values">
                <span>contact@example.com</span>
                <ArrowRight aria-hidden="true" />
                <strong>[REDACTED]</strong>
              </div>
            </div>
            <div className="access-principles">
              <ShieldCheck />
              <span>Private files. Read-only sources. Reviewed results.</span>
            </div>
          </div>
          <p className="access-story-footer">
            A focused workspace for working with your data.
          </p>
        </section>
        <form
          className="panel access-panel"
          onSubmit={async (event) => {
            event.preventDefault();
            setUnlocking(true);
            setError("");
            try {
              await api.unlock(accessPassword);
              setAccessPassword("");
              await initialize();
            } catch (value) {
              report(value);
            } finally {
              setAccessPassword("");
              setUnlocking(false);
            }
          }}
        >
          <div className="panel-head">
            <span className="access-lock">
              <LockKeyhole />
            </span>
            <h2>Open your workspace</h2>
            <p>Enter the access password to get started.</p>
          </div>
          <div className="panel-body">
            <div className="field">
              <label htmlFor="website-password">Website access password</label>
              <input
                id="website-password"
                type="password"
                required
                maxLength={256}
                autoComplete="current-password"
                value={accessPassword}
                onChange={(event) => setAccessPassword(event.target.value)}
              />
            </div>
            {error && (
              <p role="alert" className="danger-text">
                {error}
              </p>
            )}
            <button className="primary" disabled={unlocking}>
              {unlocking ? "Checking…" : "Enter workspace"}
              {!unlocking && <ArrowRight />}
            </button>
            <p className="access-disclaimer">
              This is the website entrance, not an AWS login. Your workspace is
              private to this browser.
            </p>
          </div>
        </form>
      </main>
    );
  return (
    <div className="rulecraft-app">
      <a className="skip-link" href="#main-content">
        Skip to workspace
      </a>
      <header className="app-header">
        <button
          className="brand"
          onClick={() => go("history")}
          aria-label="Rulecraft home"
        >
          <span className="brand-mark">
            <Braces />
          </span>
          Rulecraft
        </button>
        <span className="header-divider" />
        <span className="header-label">
          Workspace <ChevronRight /> <strong>{titles[screen]}</strong>
        </span>
        <div className="header-actions">
          {boot?.access_gate_enabled && (
            <button
              className="quiet"
              onClick={() => {
                void api
                  .lock()
                  .then(() => {
                    setAccessPassword("");
                    void initialize();
                  })
                  .catch(report);
              }}
            >
              <LockKeyhole />
              <span className="lock-label">Lock workspace</span>
            </button>
          )}
          <button
            className="icon-button"
            aria-label="Help"
            onClick={() => setDialog("help")}
          >
            <CircleHelp />
          </button>
          <span className="workspace-identity">
            <span className="avatar" aria-label="Guest workspace">
              G
            </span>
            <span>Guest workspace</span>
          </span>
        </div>
      </header>
      <aside className="sidebar">
        <div className="workspace-card">
          <span className="workspace-card-icon">
            <Table2 />
          </span>
          <div>
            <strong>Data workspace</strong>
            <small>Private browser session</small>
          </div>
        </div>
        <div className="workspace-label">Workspace</div>
        <nav aria-label="Main navigation">
          <button
            className={
              "nav-item " +
              (!["connection", "history", "datasets"].includes(screen)
                ? "is-active"
                : "")
            }
            onClick={prepare}
            aria-current={
              !["connection", "history", "datasets"].includes(screen)
                ? "page"
                : undefined
            }
          >
            <Table2 />
            <span>Prepare data</span>
          </button>
          <button
            className={"nav-item " + (screen === "datasets" ? "is-active" : "")}
            onClick={() => confirmDraft(() => go("datasets"))}
            aria-current={screen === "datasets" ? "page" : undefined}
          >
            <FolderClosed />
            <span>Imported datasets</span>
          </button>
          <button
            className={"nav-item " + (screen === "history" ? "is-active" : "")}
            onClick={() => go("history")}
            aria-current={screen === "history" ? "page" : undefined}
          >
            <History />
            <span>Jobs</span>
            <span className="count">{jobCount}</span>
          </button>
          <button
            className={
              "nav-item " + (screen === "connection" ? "is-active" : "")
            }
            onClick={() => go("connection")}
            aria-current={screen === "connection" ? "page" : undefined}
          >
            <Database />
            <span>Connections</span>
          </button>
        </nav>
        <div className="sidebar-end">
          <ShieldCheck />
          <div>
            <strong>Your source stays yours</strong>
            <span>Original files are never overwritten.</span>
          </div>
        </div>
      </aside>
      <nav className="mobile-nav" aria-label="Workspace navigation">
        <button
          onClick={prepare}
          className={
            !["history", "connection", "datasets"].includes(screen)
              ? "is-active"
              : ""
          }
        >
          Prepare data
        </button>
        <button
          onClick={() => go("history")}
          className={screen === "history" ? "is-active" : ""}
        >
          Jobs
        </button>
        <button
          onClick={() => confirmDraft(() => go("datasets"))}
          className={screen === "datasets" ? "is-active" : ""}
        >
          Datasets
        </button>
        <button
          onClick={() => go("connection")}
          className={screen === "connection" ? "is-active" : ""}
        >
          Connections
        </button>
      </nav>
      <main className="main-content" id="main-content">
        <div className="page-header">
          <div>
            <h1>{titles[screen]}</h1>
            {description && <p className="page-context">{description}</p>}
            {screen === "job" && job && (
              <div className="page-context job-id">
                <span title={job.id}>{job.id}</span>
                <button
                  className="icon-button"
                  aria-label="Copy job ID"
                  onClick={() =>
                    void navigator.clipboard
                      .writeText(job.id)
                      .then(() => setToast("Job ID copied."))
                      .catch(() => setToast("Select the job ID to copy it."))
                  }
                >
                  <Copy />
                </button>
                <Status job={job} />
              </div>
            )}
          </div>
          {screen === "history" || screen === "results" ? (
            <button className="primary" onClick={newJob}>
              <Plus />
              {screen === "history" ? "Create job" : "Create another job"}
            </button>
          ) : screen === "job" && job ? (
            active(job) ? (
              <button
                className="danger-button"
                disabled={job.cancel_requested}
                onClick={() => requestCancel(job)}
              >
                <Square />
                {job.cancel_requested ? "Cancelling…" : "Cancel job"}
              </button>
            ) : (
              <button onClick={() => requestReuse(job)}>
                <Copy />
                Reuse configuration
              </button>
            )
          ) : null}
        </div>
        {!["history", "datasets"].includes(screen) && (
          <nav className="steps" aria-label="Transformation steps">
            {(
              ["connection", "files", "editor", "job", "results"] as Screen[]
            ).map((value, index) => (
              <div className="step-pair" key={value}>
                <button
                  disabled={
                    !canOpen(value) ||
                    (processing && !["job", "results"].includes(value))
                  }
                  className={
                    "step " +
                    (phase === index
                      ? "is-active"
                      : phase > index
                        ? "is-done"
                        : "")
                  }
                  onClick={() => go(value)}
                  aria-current={phase === index ? "step" : undefined}
                >
                  <span className="step-circle">
                    {phase > index ? <Check /> : index + 1}
                  </span>
                  {
                    [
                      "Connect",
                      "Select file",
                      "Configure",
                      "Processing",
                      "Results",
                    ][index]
                  }
                </button>
                {index < 4 && <span className="step-line" />}
              </div>
            ))}
          </nav>
        )}
        {initializing && (
          <div className="notice" role="status">
            <LoaderCircle className="spin" />
            Connecting to your workspace…
          </div>
        )}
        {!initializing && noServices && (
          <div className="notice setup-notice">
            <Info />
            <span>Processing services need setup before jobs can run.</span>
            <button className="link" onClick={() => setDialog("help")}>
              View setup
            </button>
          </div>
        )}
        {!["history", "datasets"].includes(screen) &&
          (screen === "job" || screen === "results"
            ? job?.source_type === "sample"
            : connection?.source_type === "sample") && (
            <div className="notice warning" role="note">
              <Info />
              <span>
                <strong>Simulated S3 bucket.</strong> Synthetic, read-only
                files; not Amazon S3. Model generation, queued jobs and Spark
                processing run on the server.
              </span>
            </div>
          )}
        {boot?.sample_bucket_enabled && screen === "history" && (
          <div className="notice">
            <Database />
            <span>
              No AWS account? Use synthetic files in the simulated S3 bucket. No
              keys required.
            </span>
            <button
              disabled={connecting || processing}
              onClick={() => confirmDraft(() => void connectSample())}
            >
              {connecting ? "Connecting…" : "Try sample bucket"}
            </button>
          </div>
        )}
        {network && (
          <div className="notice warning" role="status">
            <RefreshCw />
            <span>{network} Reconnecting automatically.</span>
          </div>
        )}
        {error && (
          <div className="notice danger" role="alert">
            <CircleAlert />
            <span>{error}</span>
            <button
              className="icon-button"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              <X />
            </button>
          </div>
        )}
        {!boot && !initializing && (
          <button onClick={() => void initialize()}>
            <RefreshCw />
            Reconnect to service
          </button>
        )}
        {pendingReuse && ["connection", "files"].includes(screen) && (
          <div className="notice reuse-note">
            <Copy />
            <span>
              Reusing {pendingReuse.id.slice(0, 8)} ·{" "}
              {screen === "connection"
                ? "Connect to " +
                  (pendingReuse.bucket || "the source bucket") +
                  " to continue."
                : "Preview the source file before running the new job."}
            </span>
          </div>
        )}
        {screen === "datasets" && boot && (
          <Datasets
            onOpen={(item) => confirmDraft(() => openDataset(item))}
            onError={setError}
          />
        )}
        {screen === "history" && boot && (
          <JobsHistory
            onOpen={(item) => confirmDraft(() => void openJob(item))}
            onReuse={requestReuse}
            onCreate={newJob}
            onError={setError}
            onCount={setJobCount}
          />
        )}

        {screen === "connection" && (
          <div className="connection-layout">
            <section className="panel">
              <div className="panel-head">
                <h2>
                  <Database />
                  Amazon S3
                </h2>
                {connection && (
                  <span className="connection-active">
                    <span className="status-dot" />
                    Connected
                  </span>
                )}
              </div>
              <div className="panel-body">
                {boot?.sample_bucket_enabled && (
                  <div className="sample-card">
                    <h3>Try without AWS credentials</h3>
                    <p>
                      Simulated S3 bucket with synthetic CSV and Excel files.
                      Not Amazon S3; real server-side model and Spark
                      processing. Files cannot be changed.
                    </p>
                    <button
                      className="primary"
                      disabled={connecting || processing}
                      onClick={() => confirmDraft(() => void connectSample())}
                    >
                      {connecting ? (
                        <LoaderCircle className="spin" />
                      ) : (
                        <Database />
                      )}
                      {connecting ? "Connecting…" : "Use sample bucket"}
                    </button>
                    <small>Or connect your own Amazon S3 bucket below.</small>
                  </div>
                )}
                {connections.length > 0 && (
                  <div className="saved-connections">
                    <label htmlFor="saved-connection">Saved connections</label>
                    <div className="inline-fields">
                      <select
                        id="saved-connection"
                        value={connection?.id || ""}
                        onChange={(event) => {
                          const next = connections.find(
                            (item) => item.id === event.target.value,
                          );
                          if (next) {
                            clearDraft();
                            setConnection(next);
                            setFiles([]);
                            setPrefix("");
                          }
                        }}
                      >
                        <option value="" disabled>
                          Choose a connection
                        </option>
                        {connections.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.bucket} ·{" "}
                            {item.source_type === "sample"
                              ? "Simulated S3"
                              : item.region}
                          </option>
                        ))}
                      </select>
                      <button
                        className="primary"
                        disabled={!connection || processing}
                        onClick={() => {
                          if (connection) {
                            go("files");
                            void loadFiles(connection, prefix);
                          }
                        }}
                      >
                        Continue
                        <ArrowRight />
                      </button>
                    </div>
                    {connection && (
                      <div className="saved-meta">
                        <span>Expires {dateLabel(connection.expires_at)}</span>
                        <button
                          className="link danger-text"
                          disabled={submitting}
                          onClick={() => setDialog("disconnect")}
                        >
                          Disconnect
                        </button>
                      </div>
                    )}
                  </div>
                )}
                <form
                  onSubmit={(event) => void connect(event)}
                  autoComplete="off"
                >
                  <p className="inline-note">
                    Connect bucket authorizes this workspace to list and import
                    your S3 files; it does not log you into the website. New
                    connections expire after{" "}
                    {boot?.limits.credential_ttl_hours || 1} hour(s). Imported
                    datasets are retained separately.
                  </p>
                  <div className="field">
                    <label htmlFor="access-key">AWS access key ID</label>
                    <input
                      id="access-key"
                      required
                      minLength={3}
                      maxLength={128}
                      spellCheck={false}
                      autoCapitalize="off"
                      autoComplete="off"
                      value={credentials.access_key}
                      onChange={(e) =>
                        setCredentials({
                          ...credentials,
                          access_key: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="secret-key">AWS secret access key</label>
                    <div className="secret-input">
                      <input
                        id="secret-key"
                        required
                        minLength={8}
                        maxLength={256}
                        type={showSecret ? "text" : "password"}
                        autoComplete="new-password"
                        value={credentials.secret_key}
                        onChange={(e) =>
                          setCredentials({
                            ...credentials,
                            secret_key: e.target.value,
                          })
                        }
                      />
                      <button
                        type="button"
                        className="link"
                        aria-pressed={showSecret}
                        onClick={() => setShowSecret(!showSecret)}
                      >
                        {showSecret ? "Hide" : "Show"}
                      </button>
                    </div>
                  </div>
                  <div className="field">
                    <label htmlFor="bucket">Bucket name</label>
                    <input
                      id="bucket"
                      required
                      maxLength={255}
                      placeholder="my-data-bucket"
                      spellCheck={false}
                      value={credentials.bucket}
                      onChange={(e) =>
                        setCredentials({
                          ...credentials,
                          bucket: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="region">AWS region</label>
                    <input
                      id="region"
                      required
                      maxLength={32}
                      placeholder="us-east-1"
                      value={credentials.region}
                      onChange={(e) =>
                        setCredentials({
                          ...credentials,
                          region: e.target.value,
                        })
                      }
                    />
                  </div>
                  <details className="advanced">
                    <summary>Temporary credentials (optional)</summary>
                    <div className="field">
                      <label htmlFor="session-token">STS session token</label>
                      <input
                        id="session-token"
                        type="password"
                        maxLength={4096}
                        autoComplete="new-password"
                        value={credentials.session_token}
                        onChange={(e) =>
                          setCredentials({
                            ...credentials,
                            session_token: e.target.value,
                          })
                        }
                      />
                      <small>Required for temporary AWS sessions.</small>
                    </div>
                  </details>
                  <button
                    type="submit"
                    className="primary"
                    disabled={connecting || !boot || processing}
                  >
                    {connecting ? (
                      <LoaderCircle className="spin" />
                    ) : (
                      <Database />
                    )}
                    {connecting ? "Connecting…" : "Connect to S3"}
                  </button>
                  <p className="inline-note">
                    <LockKeyhole />
                    Only list and read access is required.
                  </p>
                </form>
              </div>
            </section>
            <aside className="connection-guide">
              <div className="guide-symbol">
                <Braces />
              </div>
              <h2>One rule, every row.</h2>
              <p>
                Start with a private S3 source. Tell Rulecraft what should
                change, without writing a script.
              </p>
              <ol>
                <li>
                  <div>
                    <strong>Bring your data</strong>
                    <span>Select a CSV or an Excel worksheet.</span>
                  </div>
                </li>
                <li>
                  <div>
                    <strong>Describe the change</strong>
                    <span>Replace, extract or standardize text.</span>
                  </div>
                </li>
                <li>
                  <div>
                    <strong>Review the result</strong>
                    <span>Browse every row. Keep the source intact.</span>
                  </div>
                </li>
              </ol>
              <div className="privacy-note">
                <ShieldCheck />
                <p>
                  Your credentials are encrypted on the server. Keys and file
                  rows are never sent to the language model.
                </p>
              </div>
              <p className="muted">
                Original files remain unchanged. Use Imported datasets after a
                connection expires; retained imports remain usable for{" "}
                {boot?.limits.dataset_ttl_hours || 24} hours.
              </p>
            </aside>
          </div>
        )}

        {screen === "files" && (
          <>
            <form
              className="file-toolbar"
              onSubmit={(event) => {
                event.preventDefault();
                if (connection) void loadFiles(connection, prefix);
              }}
            >
              <div className="search-field">
                <Search />
                <input
                  aria-label="S3 prefix"
                  placeholder="Filter by path prefix, e.g. reports/"
                  value={prefix}
                  maxLength={1024}
                  onChange={(e) => setPrefix(e.target.value)}
                />
              </div>
              <button type="submit" disabled={loadingFiles || processing}>
                <RefreshCw className={loadingFiles ? "spin" : ""} />
                Refresh files
              </button>
            </form>
            <section className="panel">
              <div className="table-wrap">
                <table className="files-table" aria-label="Source files">
                  <thead>
                    <tr>
                      <th aria-label="Selection" />
                      <th>File path</th>
                      <th>Size</th>
                      <th>Last modified</th>
                      <th>Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((file) => (
                      <tr
                        key={file.key}
                        className={
                          file.key === selected?.key
                            ? "file-active"
                            : !file.supported
                              ? "file-disabled"
                              : ""
                        }
                      >
                        <td>
                          <input
                            type="radio"
                            name="source-file"
                            aria-label={"Select " + file.key}
                            disabled={
                              !file.supported || processing || loadingFiles
                            }
                            checked={file.key === selected?.key}
                            onChange={() => chooseFile(file)}
                          />
                        </td>
                        <td>
                          <span className="file-name">
                            <FileSpreadsheet />
                            {file.key}
                          </span>
                          {file.description && (
                            <small className="sample-description">
                              {file.description}
                            </small>
                          )}
                        </td>
                        <td>{formatBytes(file.size)}</td>
                        <td>{dateLabel(file.modified)}</td>
                        <td>
                          {file.key.split(".").pop()?.toUpperCase()}
                          {!file.supported && " · Unsupported"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!files.length && (
                <div className="empty compact" role="status">
                  {loadingFiles
                    ? "Loading source files…"
                    : "No files match this path. Try a different prefix."}
                </div>
              )}
              <div className="table-bottom">
                <span>{files.length} files loaded</span>
                {fileCursor ? (
                  <button
                    className="link"
                    disabled={loadingFiles || !connection}
                    onClick={() =>
                      connection &&
                      void loadFiles(connection, prefix, fileCursor, true)
                    }
                  >
                    Load more files
                  </button>
                ) : (
                  <span>Original files will not be modified</span>
                )}
              </div>
            </section>
            {selected && (
              <div className="file-options">
                {selected.key.toLowerCase().endsWith(".xlsx") ? (
                  <div className="field">
                    <label htmlFor="worksheet">Worksheet</label>
                    {sheets.length ? (
                      <select
                        id="worksheet"
                        disabled={processing}
                        value={sheet}
                        onChange={(e) => {
                          setSheet(e.target.value);
                          resetInspection();
                        }}
                      >
                        <option value="">Select a worksheet</option>
                        {sheets.map((name) => (
                          <option key={name}>{name}</option>
                        ))}
                      </select>
                    ) : (
                      <p className="muted">
                        Preview this workbook to discover its worksheets.
                      </p>
                    )}
                  </div>
                ) : (
                  <details className="advanced">
                    <summary>CSV settings</summary>
                    <div className="two-fields">
                      <div className="field">
                        <label htmlFor="encoding">Encoding</label>
                        <select
                          id="encoding"
                          value={encoding}
                          disabled={processing}
                          onChange={(e) => {
                            setEncoding(e.target.value);
                            resetInspection();
                          }}
                        >
                          {["UTF-8", "UTF-16", "ISO-8859-1"].map((value) => (
                            <option key={value}>{value}</option>
                          ))}
                        </select>
                      </div>
                      <div className="field">
                        <label htmlFor="delimiter">Delimiter</label>
                        <select
                          id="delimiter"
                          value={delimiter}
                          disabled={processing}
                          onChange={(e) => {
                            setDelimiter(e.target.value);
                            resetInspection();
                          }}
                        >
                          {[
                            [",", "Comma"],
                            [";", "Semicolon"],
                            ["\t", "Tab"],
                            ["|", "Pipe"],
                          ].map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    <small>
                      The first row contains column names. Values are read as
                      text.
                    </small>
                  </details>
                )}
              </div>
            )}
            {inspection && active(inspection) && (
              <div className="notice" role="status">
                <LoaderCircle className="spin" />
                <span>
                  {stageLabels[inspection.stage] || "Reading source…"}
                </span>
                <button
                  className="link"
                  disabled={inspection.cancel_requested}
                  onClick={() => requestCancel(inspection)}
                >
                  Cancel preview
                </button>
              </div>
            )}
            {inspection?.status === "FAILED" && (
              <div className="notice danger" role="alert">
                <CircleAlert />
                <span>
                  {inspection.error?.message ||
                    "The file could not be read. Check your connection and parsing options."}
                </span>
              </div>
            )}
            <div className="file-bottom">
              <button className="quiet" onClick={() => go("connection")}>
                <ArrowLeft />
                Back
              </button>
              <button
                className="primary"
                disabled={
                  !selected ||
                  processing ||
                  submitting ||
                  !boot ||
                  (sheets.length > 0 && !sheet)
                }
                onClick={() => void inspectFile()}
              >
                {submitting || active(inspection) ? (
                  <LoaderCircle className="spin" />
                ) : (
                  <ArrowRight />
                )}
                {submitting || active(inspection)
                  ? "Reading file…"
                  : "Preview selected file"}
              </button>
            </div>
          </>
        )}

        {screen === "editor" && (
          <>
            {reusedFrom && (
              <div className="notice reuse-note">
                <Copy />
                <span>
                  New draft from {reusedFrom.slice(0, 8)} · The original job is
                  unchanged.
                </span>
              </div>
            )}
            <div className="source-bar">
              <FileSpreadsheet />
              <strong>
                {selected ? filename(selected.key) : "Source data"}
                {sheet ? " / " + sheet : ""}
              </strong>
              <span className="format-tag">
                {selected?.key.toLowerCase().endsWith(".xlsx") ? "XLSX" : "CSV"}
              </span>
              <button
                className="link"
                disabled={processing}
                onClick={() => go("files")}
              >
                Change file
                <ChevronRight />
              </button>
            </div>
            <div className="editor-layout">
              <section className="source-data">
                <div className="panel-head">
                  <h2>Source preview</h2>
                  <span>
                    {schema.length} columns · up to{" "}
                    {boot?.limits.preview_rows || 100} preview rows
                  </span>
                </div>
                {schema.length ? (
                  <DataTable
                    rows={inputPreview}
                    columns={schema}
                    selected={columns}
                    onToggleColumn={toggleColumn}
                  />
                ) : (
                  <div className="empty">
                    <p>Preview the selected source to configure a job.</p>
                    <button onClick={() => go("files")}>Select file</button>
                  </div>
                )}
                <div className="table-bottom">
                  <span>
                    Previewing {inputPreview.length} rows · Click a column to
                    select it
                  </span>
                  <span>
                    <LockKeyhole />
                    Read-only
                  </span>
                </div>
              </section>
              <section
                className="configuration"
                aria-label="Transformation configuration"
              >
                <div className="panel-head">
                  <h2>Transformation</h2>
                  <span className="selection-count" aria-live="polite">
                    {columns.length} selected
                  </span>
                </div>
                <form
                  className="config-body"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const issue = validateDraft();
                    if (issue) setError(issue);
                    else {
                      setError("");
                      setDialog("review");
                    }
                  }}
                >
                  <div
                    className="operation-tabs"
                    role="group"
                    aria-label="Transformation type"
                  >
                    {(
                      [
                        ["regex_replace", "Replace"],
                        ["regex_extract", "Extract"],
                        ["normalize", "Standardize"],
                      ] as [Operation, string][]
                    ).map(([value, label]) => (
                      <button
                        type="button"
                        key={value}
                        className={operation === value ? "is-active" : ""}
                        aria-pressed={operation === value}
                        onClick={() => {
                          setOperation(value);
                          setPrompt("");
                          setError("");
                          if (value === "regex_extract")
                            setColumns((old) => old.slice(0, 1));
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <fieldset className="field target-field">
                    <legend>
                      {operation === "regex_extract"
                        ? "Source column"
                        : "Columns to update"}
                    </legend>
                    <div className="column-checks">
                      {schema.map((column) => (
                        <label
                          key={column.name}
                          className={
                            columns.includes(column.name) ? "chosen" : ""
                          }
                        >
                          <input
                            type={
                              operation === "regex_extract"
                                ? "radio"
                                : "checkbox"
                            }
                            name="target-columns"
                            value={column.name}
                            checked={columns.includes(column.name)}
                            onChange={() => toggleColumn(column.name)}
                          />
                          {column.name}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                  <div className="field">
                    <div className="field-label">
                      <label htmlFor="instruction">
                        {operation === "regex_replace"
                          ? "Describe what to find"
                          : operation === "regex_extract"
                            ? "Describe what to extract"
                            : "Describe the formatting"}
                      </label>
                      <button
                        type="button"
                        className="link example"
                        onClick={() => setPrompt(examples[operation])}
                      >
                        Use example
                      </button>
                    </div>
                    <textarea
                      id="instruction"
                      spellCheck={false}
                      maxLength={4000}
                      rows={4}
                      placeholder={"e.g. " + examples[operation]}
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                    />
                    {operation === "regex_extract" && (
                      <small>
                        For custom IDs, specify the prefix and format, e.g. ORD-
                        followed by one or more digits. Data rows are not sent
                        to the model.
                      </small>
                    )}
                  </div>
                  {operation === "regex_replace" ? (
                    <div className="field">
                      <label htmlFor="replacement">Replacement text</label>
                      <input
                        id="replacement"
                        maxLength={4000}
                        placeholder="e.g. REDACTED"
                        value={replacement}
                        disabled={removeMatches}
                        onChange={(e) => setReplacement(e.target.value)}
                      />
                      <label className="remove-option">
                        <input
                          type="checkbox"
                          checked={removeMatches}
                          onChange={(e) => setRemoveMatches(e.target.checked)}
                        />
                        Remove matched text instead
                      </label>
                    </div>
                  ) : operation === "regex_extract" ? (
                    <div className="field">
                      <label htmlFor="new-column">New column name</label>
                      <input
                        id="new-column"
                        maxLength={128}
                        placeholder="e.g. order_id"
                        value={newColumn}
                        onChange={(e) => setNewColumn(e.target.value)}
                      />
                      <small>
                        First match only. The source column is kept.
                      </small>
                    </div>
                  ) : (
                    <p className="muted">
                      Supports whitespace cleanup and letter case.
                    </p>
                  )}
                  <div className="config-bottom">
                    <button
                      type="submit"
                      className="primary"
                      disabled={submitting || processing || !schema.length}
                    >
                      Review job
                      <ArrowRight />
                    </button>
                  </div>
                </form>
              </section>
            </div>
          </>
        )}

        {screen === "job" && job && (
          <>
            <div className="job-links">
              <button className="quiet" onClick={() => go("history")}>
                <ArrowLeft />
                Back to jobs
              </button>
            </div>
            {job.error && (
              <div className="notice danger">
                <CircleAlert />
                <div>
                  <strong>{job.error.message}</strong>
                  <p>
                    Check source permissions and your instruction, then reuse
                    this configuration to create a new job.
                  </p>
                  <small>Error code: {job.error.code}</small>
                </div>
              </div>
            )}
            {job.stage === "RETRYING" && (
              <div className="notice warning">
                <RefreshCw />
                <span>
                  Temporary service problem. We will retry automatically; do not
                  submit a duplicate job.
                </span>
              </div>
            )}
            {job.status === "CANCELLED" && (
              <div className="notice">
                <CircleAlert />
                <span>
                  Job cancelled. No result was published. The original file is
                  unchanged.
                </span>
              </div>
            )}
            {resultExpired(job) && (
              <div className="notice warning">
                <Clock3 />
                <span>
                  This job succeeded, but its results have expired. The record
                  and configuration remain available.
                </span>
              </div>
            )}
            <div className="job-layout">
              <section className="panel">
                <div className="panel-head">
                  <h2>Progress</h2>
                  <span>Attempt {Math.max(1, job.attempt)} of 3</span>
                </div>
                <div className="panel-body">
                  <div className="progress-row">
                    <span>
                      {job.cancel_requested && active(job)
                        ? "Stopping computation"
                        : stageLabels[job.stage] || job.stage}
                    </span>
                    <span>{job.progress}%</span>
                  </div>
                  <div
                    className="track"
                    role="progressbar"
                    aria-label="Estimated progress"
                    aria-valuenow={job.progress}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="fill"
                      style={{ width: job.progress + "%" }}
                    />
                  </div>
                  <ol className="timeline">
                    {stages.map((stage, index) => {
                      const current = stage === job.stage,
                        done =
                          job.status === "SUCCESS" ||
                          stages.indexOf(job.stage) > index;
                      return (
                        <li
                          key={stage}
                          className={done ? "done" : current ? "current" : ""}
                        >
                          <span>
                            {done ? (
                              <Check />
                            ) : current && active(job) ? (
                              <LoaderCircle className="spin" />
                            ) : (
                              <Circle />
                            )}
                          </span>
                          <span>{stageLabels[stage]}</span>
                          <small>
                            {done
                              ? "Done"
                              : current
                                ? active(job)
                                  ? "In progress"
                                  : "Stopped"
                                : ""}
                          </small>
                        </li>
                      );
                    })}
                  </ol>
                  <p className="inline-note">
                    <Info />
                    Estimated progress, based on the current stage.
                  </p>
                  {job.status === "SUCCESS" && !resultExpired(job) && (
                    <button className="primary" onClick={() => go("results")}>
                      View results
                      <ArrowRight />
                    </button>
                  )}
                </div>
              </section>
              <section className="panel">
                <div className="panel-head">
                  <h2>Configuration</h2>
                </div>
                <div className="panel-body">
                  <dl className="key-values">
                    <dt>Source</dt>
                    <dd>
                      {job.source_key}
                      {jobConfig.sheet ? " / " + jobConfig.sheet : ""}
                    </dd>
                    <dt>Operation</dt>
                    <dd>
                      {operationLabel(
                        String(jobConfig.operation || job.operation || ""),
                      )}
                    </dd>
                    <dt>Columns</dt>
                    <dd>
                      {((jobConfig.target_columns as string[]) || []).join(
                        ", ",
                      )}
                    </dd>
                    {jobConfig.operation === "regex_replace" && (
                      <>
                        <dt>Replace with</dt>
                        <dd>
                          {jobConfig.replacement === ""
                            ? "Remove matched text"
                            : String(jobConfig.replacement)}
                        </dd>
                      </>
                    )}
                    {jobConfig.operation === "regex_extract" && (
                      <>
                        <dt>New column</dt>
                        <dd>{String(jobConfig.new_column)}</dd>
                      </>
                    )}
                    <dt>Created</dt>
                    <dd>{dateLabel(job.created_at)}</dd>
                    <dt>Duration</dt>
                    <dd>{durationLabel(job)}</dd>
                  </dl>
                  <div className="prompt-summary">
                    <h3>Instruction</h3>
                    <p>{String(jobConfig.prompt || "")}</p>
                  </div>
                  {job.plan && (job.plan.pattern || job.plan.steps?.length) && (
                    <details className="validated-rule">
                      <summary>
                        Validated rule{" "}
                        {job.metadata?.cache_hit ? "· cached" : ""}
                      </summary>
                      <code>
                        {job.plan.pattern || job.plan.steps?.join(" → ")}
                      </code>
                      <p>{job.plan.explanation}</p>
                    </details>
                  )}
                </div>
              </section>
            </div>
          </>
        )}

        {screen === "results" && job && (
          <>
            <div className="job-links">
              <button className="quiet" onClick={() => go("history")}>
                <ArrowLeft />
                Back to jobs
              </button>
              <button className="quiet" onClick={() => requestReuse(job)}>
                <Copy />
                Reuse configuration
              </button>
            </div>
            {resultExpired(job) ? (
              <section className="panel">
                <div className="empty">
                  <Clock3 />
                  <h2>Results are no longer available</h2>
                  <p>
                    The job record is kept. Reuse its configuration to generate
                    new results.
                  </p>
                  <button className="primary" onClick={() => requestReuse(job)}>
                    <Copy />
                    Reuse configuration
                  </button>
                </div>
              </section>
            ) : (
              <>
                <div className="job-complete">
                  <Check />
                  <strong>Job completed</strong>
                  <button className="link" onClick={() => go("job")}>
                    Job details
                    <ArrowRight />
                  </button>
                </div>
                {changed === 0 && (
                  <div className="notice">
                    <Info />
                    <span>
                      No values were changed or extracted. All original rows
                      remain in the result.
                    </span>
                  </div>
                )}
                <div className="result-info">
                  <span>
                    <strong>
                      {(
                        job.metadata?.row_count ||
                        page?.total_rows ||
                        0
                      ).toLocaleString()}
                    </strong>{" "}
                    rows processed
                  </span>
                  <span>
                    <strong>{changed.toLocaleString()}</strong>{" "}
                    {jobConfig.operation === "regex_extract"
                      ? "rows extracted"
                      : "cells updated"}
                  </span>
                  {job.result_expires_at && (
                    <span className="retention">
                      <Clock3 />
                      Available until {dateLabel(job.result_expires_at)}
                    </span>
                  )}
                </div>
                <section className="panel">
                  <div className="result-toolbar">
                    <h2>Data</h2>
                    <div
                      className="segment"
                      role="group"
                      aria-label="Data view"
                    >
                      <button
                        className={dataView === "result" ? "is-active" : ""}
                        aria-pressed={dataView === "result"}
                        onClick={() => setDataView("result")}
                      >
                        Result
                      </button>
                      <button
                        disabled={!schema.length}
                        className={dataView === "original" ? "is-active" : ""}
                        aria-pressed={dataView === "original"}
                        onClick={() => setDataView("original")}
                      >
                        Original preview
                      </button>
                    </div>
                  </div>
                  {dataView === "original" ? (
                    <>
                      <div className="table-hint">
                        Bounded source preview only. Result rows may be in a
                        different order; this is not a row-by-row comparison.
                      </div>
                      <DataTable rows={inputPreview} columns={schema} />
                      <div className="table-bottom">
                        {inputPreview.length} original preview rows · Read-only
                      </div>
                    </>
                  ) : (
                    <>
                      {loadingPage ? (
                        <div className="empty compact" role="status">
                          <LoaderCircle className="spin" />
                          Loading result page…
                        </div>
                      ) : page ? (
                        <DataTable
                          rows={page.rows}
                          columns={page.columns}
                          selected={
                            (jobConfig.target_columns as string[]) || []
                          }
                          offset={page.offset}
                        />
                      ) : (
                        <div className="empty compact">
                          <p>Result data is not loaded.</p>
                          <button onClick={() => void loadPage(job, "", 0)}>
                            Retry loading
                          </button>
                        </div>
                      )}
                      <div className="table-bottom">
                        <span>
                          {page
                            ? (page.returned_rows ? page.offset + 1 : 0) +
                              "–" +
                              (page.offset + page.returned_rows) +
                              " of " +
                              page.total_rows.toLocaleString() +
                              " rows"
                            : "Loading…"}
                        </span>
                        <div
                          className="pagination"
                          aria-label="Results pagination"
                        >
                          <label className="page-size">
                            Rows
                            <select
                              aria-label="Rows per page"
                              value={pageSize}
                              disabled={loadingPage}
                              onChange={(e) =>
                                setPageSize(Number(e.target.value))
                              }
                            >
                              {[25, 100, 250, 500].map((size) => (
                                <option key={size}>{size}</option>
                              ))}
                            </select>
                          </label>
                          <button
                            className="icon-button"
                            aria-label="Previous page"
                            disabled={pageNumber === 0 || loadingPage}
                            onClick={() =>
                              void loadPage(
                                job,
                                cursors[pageNumber - 1],
                                pageNumber - 1,
                              )
                            }
                          >
                            <ChevronLeft />
                          </button>
                          <span>Page {pageNumber + 1}</span>
                          <button
                            className="icon-button"
                            aria-label="Next page"
                            disabled={!page?.next_cursor || loadingPage}
                            onClick={() => {
                              if (!page?.next_cursor) return;
                              setCursors([
                                ...cursors.slice(0, pageNumber + 1),
                                page.next_cursor,
                              ]);
                              void loadPage(
                                job,
                                page.next_cursor,
                                pageNumber + 1,
                              );
                            }}
                          >
                            <ChevronRight />
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </section>
                <p className="inline-note">
                  <LockKeyhole />
                  Source unchanged. Highlighted columns indicate transformation
                  targets, not a cell-by-cell diff.
                </p>
              </>
            )}
          </>
        )}
      </main>
      <footer className="statusbar">
        <span>
          {connection ? (
            <>
              <span className="status-dot" />
              {new Date(connection.expires_at).getTime() <= Date.now()
                ? "Imported dataset · "
                : connection.source_type === "sample"
                  ? "Simulated S3 · "
                  : "Connected to "}
              {connection.bucket}
            </>
          ) : (
            "No active connection"
          )}
        </span>
        <span>Source files remain unchanged</span>
      </footer>
      {toast && (
        <div className="toast" role="status">
          {toast}
        </div>
      )}
      {dialog && (
        <Modal
          title={
            {
              help: "Rulecraft help",
              review: "Review job",
              cancel: "Cancel this job?",
              disconnect: "Disconnect from S3?",
              discard: "Replace the current draft?",
            }[dialog]
          }
          onClose={() => {
            if (!submitting) setDialog(null);
          }}
          actions={
            dialog === "help" ? (
              <button className="primary" onClick={() => setDialog(null)}>
                Got it
              </button>
            ) : (
              <>
                <button disabled={submitting} onClick={() => setDialog(null)}>
                  Keep{" "}
                  {dialog === "cancel"
                    ? "running"
                    : dialog === "discard"
                      ? "draft"
                      : dialog === "disconnect"
                        ? "connection"
                        : "editing"}
                </button>
                <button
                  className={
                    dialog === "cancel" || dialog === "disconnect"
                      ? "danger-button"
                      : "primary"
                  }
                  disabled={submitting}
                  onClick={() => {
                    if (dialog === "review") void submit();
                    else if (dialog === "cancel") void cancel();
                    else if (dialog === "disconnect") void disconnect();
                    else {
                      setDialog(null);
                      const action = pendingAction.current;
                      pendingAction.current = null;
                      action?.();
                    }
                  }}
                >
                  {submitting && <LoaderCircle className="spin" />}
                  {dialog === "review"
                    ? "Run job"
                    : dialog === "cancel"
                      ? "Cancel job"
                      : dialog === "disconnect"
                        ? "Disconnect"
                        : "Replace draft"}
                </button>
              </>
            )
          }
        >
          {dialog === "help" ? (
            <>
              <p>
                Connect your own Amazon S3 bucket, preview a CSV or Excel
                worksheet, choose columns and describe a transformation. Review
                the configuration before running the job.
              </p>
              {boot?.sample_bucket_enabled && (
                <p className="muted">
                  The optional sample bucket uses synthetic, read-only files
                  without AWS credentials. It is not Amazon S3 and does not
                  prove real S3 access. All processing jobs still run on the
                  server.
                </p>
              )}
              <h3>Processing service status</h3>
              <div className="service-list">
                {["database", "queue", "worker", "spark", "llm_configured"].map(
                  (name) => (
                    <div key={name}>
                      <span>
                        {
                          {
                            database: "Database",
                            queue: "Task queue",
                            worker: "Processing worker",
                            spark: "Spark connection",
                            llm_configured: "Model configured",
                          }[name]
                        }
                      </span>
                      <span
                        className={
                          services[name] ? "success-text" : "warning-text"
                        }
                      >
                        {services[name] ? "Ready" : "Needs setup"}
                      </span>
                    </div>
                  ),
                )}
              </div>
              <p className="muted">
                A configured model does not guarantee provider availability.
                Actual failures are reported; results are never fabricated.
              </p>
              <h3>Safety and retention</h3>
              <p>
                Source files are read-only. Connections expire after{" "}
                {boot?.limits.credential_ttl_hours || 1} hour(s); imported
                datasets and results are retained separately for{" "}
                {boot?.limits.dataset_ttl_hours || 24} hours. Jobs belong to
                this browser session. Never include keys in a recording.
              </p>
            </>
          ) : dialog === "review" ? (
            <>
              <p>
                Confirm your configuration. A new asynchronous job will be
                created; your source file will not change.
              </p>
              <dl className="key-values">
                <dt>Source</dt>
                <dd>
                  {selected?.key}
                  {sheet ? " / " + sheet : ""}
                </dd>
                <dt>Operation</dt>
                <dd>{operationLabel(operation)}</dd>
                <dt>Columns</dt>
                <dd>{columns.join(", ")}</dd>
                <dt>Instruction</dt>
                <dd>{prompt}</dd>
                {operation === "regex_replace" && (
                  <>
                    <dt>Replace with</dt>
                    <dd>
                      {removeMatches ? "Remove matched text" : replacement}
                    </dd>
                  </>
                )}
                {operation === "regex_extract" && (
                  <>
                    <dt>New column</dt>
                    <dd>{newColumn}</dd>
                  </>
                )}
              </dl>
              <p className="inline-note">
                <LockKeyhole />
                Replacement is literal. No sample rows or AWS keys are sent to
                the model.
              </p>
            </>
          ) : dialog === "cancel" ? (
            <p>
              The server will stop this{" "}
              {cancelTarget?.kind === "inspect"
                ? "file preview"
                : "processing job"}
              . No partial result will be published. Your original file remains
              unchanged.
            </p>
          ) : dialog === "disconnect" ? (
            <p>
              New imports will require reconnecting. Credentials are removed
              after any active import finishes. Available imported datasets and
              snapshot-based processing remain usable until their own expiry.
            </p>
          ) : (
            <p>
              Your unsent configuration will be replaced. Existing and running
              jobs on the server are not modified.
            </p>
          )}
          {submitting && (
            <p className="inline-note" role="status">
              Submitting request…
            </p>
          )}
          {error && (
            <p className="danger-text" role="alert">
              {error}
            </p>
          )}
        </Modal>
      )}
    </div>
  );
}
