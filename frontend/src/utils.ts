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
export const stageLabels: Record<string, string> = {
  QUEUED: "Waiting for an available worker",
  VALIDATING: "Validating source and configuration",
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
