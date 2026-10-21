import { useEffect, useState } from "react";
import { Clock3, Database, FileSpreadsheet, RefreshCw } from "lucide-react";
import { api } from "../api";
import type { Job } from "../api";
import { dateLabel, filename } from "../utils";

export function Datasets({
  onOpen,
  onError,
}: {
  onOpen: (item: Job) => void;
  onError: (message: string) => void;
}) {
  const [items, setItems] = useState<Job[]>([]),
    [loading, setLoading] = useState(true);
  async function load() {
    setLoading(true);
    try {
      setItems((await api.datasets()).datasets);
    } catch (error) {
      onError(
        error instanceof Error ? error.message : "Unable to load datasets.",
      );
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  return (
    <section className="panel" aria-busy={loading}>
      <div className="panel-head">
        <h2>
          <Database /> Imported datasets
        </h2>
        <button disabled={loading} onClick={() => void load()}>
          <RefreshCw /> Refresh datasets
        </button>
      </div>
      <div className="panel-body">
        <p className="muted">
          Imported files are private to this browser session. They remain usable
          after the S3 connection expires, until the dataset retention time
          shown below. Original S3 files are not modified.
        </p>
        {!items.length ? (
          <div className="empty">
            {loading
              ? "Loading datasets…"
              : "No imported datasets yet. Connect a bucket and preview a file to import it."}
          </div>
        ) : (
          <div className="dataset-list">
            {items.map((item) => (
              <article className="dataset-card" key={item.id}>
                <div className="dataset-title">
                  <span className="dataset-icon">
                    <FileSpreadsheet />
                  </span>
                  <h3>
                    {filename(item.source_key)}
                    {item.metadata?.sheet ? " · " + item.metadata.sheet : ""}
                  </h3>
                  <span className="format-tag">
                    {item.source_key.toLowerCase().endsWith(".xlsx")
                      ? "XLSX"
                      : "CSV"}
                  </span>
                </div>
                <p className="dataset-source">
                  {item.source_type === "sample"
                    ? "Simulated source"
                    : "Imported from Amazon S3"}
                </p>
                <p className="dataset-bucket">{item.bucket}</p>
                <div className="dataset-dates">
                  <small>
                    Imported {dateLabel(item.finished_at || item.created_at)}
                  </small>
                  <small>
                    <Clock3 /> Retained until{" "}
                    {dateLabel(item.dataset_expires_at || "")}
                  </small>
                </div>
                <button onClick={() => onOpen(item)}>
                  Use imported dataset
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
