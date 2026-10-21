import type { Job } from "./api";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
}
export const active = (job: Job | null) =>
  !!job && ["QUEUED", "RUNNING"].includes(job.status);
export const filename = (key: string) => key.split("/").pop() || key;
export const resultExpired = (job: Job, now = Date.now()) =>
  job.status === "SUCCESS" &&
  job.kind === "transform" &&
  (!job.result_available ||
    !job.result_expires_at ||
    new Date(job.result_expires_at).getTime() <= now);
export function durationLabel(job: Job, now = Date.now()) {
  if (!job.started_at) return job.status === "QUEUED" ? "Queued" : "—";
  const seconds = Math.max(
    0,
    Math.round(
      ((job.finished_at ? new Date(job.finished_at).getTime() : now) -
        new Date(job.started_at).getTime()) /
        1000,
    ),
  );
  return seconds < 60
    ? `${seconds}s`
    : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
export const operationLabel = (operation?: string) =>
  ({
    regex_replace: "Find and replace",
    regex_extract: "Extract values",
    normalize: "Standardize text",
  })[operation || ""] || "File inspection";
export function dateLabel(value: string) {
  return new Intl.DateTimeFormat("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Australia/Sydney",
  }).format(new Date(value));
}
export const stageLabels: Record<string, string> = {
  QUEUED: "Waiting for an available worker",
  VALIDATING: "Validating source and configuration",
  IMPORTING: "Importing a private dataset snapshot",
  GENERATING_PLAN: "Turning your instruction into a rule",
  VALIDATING_RULE: "Checking rule safety",
  READING: "Reading your source data",
  TRANSFORMING: "Transforming data across partitions",
  WRITING: "Saving and indexing your results",
  COMPLETED: "Your results are ready",
  RETRYING: "Waiting to retry a temporary failure",
  RECOVERING: "Recovering an interrupted task",
  CANCELLING: "Stopping the running computation",
  CANCELLED: "Task cancelled",
  FAILED: "Task could not finish",
};
