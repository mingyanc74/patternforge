export type Connection = {
  id: string;
  bucket: string;
  region: string;
  expires_at: string;
};
export type SourceFile = {
  key: string;
  size: number;
  modified: string;
  supported: boolean;
};
export type Column = { name: string; type: string };
export type Operation = "regex_replace" | "regex_extract" | "normalize";
export type Job = {
  id: string;
  kind: "inspect" | "transform";
  source_key: string;
  connection_id: string;
  status: "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED" | "CANCELLED";
  stage: string;
  progress: number;
  attempt: number;
  cancel_requested: boolean;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  result_expires_at: string | null;
  result_available: boolean;
  error: { code: string; message: string } | null;
  config?: Record<string, unknown>;
  plan?: {
    operation: Operation;
    pattern: string | null;
    steps: string[];
    explanation: string;
  };
  metadata?: {
    columns?: Column[];
    preview?: Record<string, unknown>[];
    sheets?: string[];
    sheet?: string;
    requires_sheet?: boolean;
    row_count?: number;
    changed_cells?: Record<string, number>;
    cache_hit?: boolean;
    spark_seconds?: number;
    partitions?: number;
  };
};
export type ResultPage = {
  rows: Record<string, unknown>[];
  columns: Column[];
  total_rows: number;
  offset: number;
  returned_rows: number;
  next_cursor: string | null;
  version: string;
};
export type Bootstrap = {
  csrf_token: string;
  llm_configured: boolean;
  limits: {
    preview_rows: number;
    max_page_rows: number;
    max_file_bytes: number;
    max_excel_bytes: number;
    result_ttl_hours: number;
  };
};

let csrf = "";
export class RequestError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}
export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 35000);
  try {
    const response = await fetch("/api" + path, {
      ...options,
      credentials: "same-origin",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
        ...options.headers,
      },
    });
    if (response.status === 204) return undefined as T;
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const error = body?.error;
      const details = error?.details
        ? " " + JSON.stringify(error.details).slice(0, 400)
        : "";
      throw new RequestError(
        error?.code || "REQUEST_FAILED",
        (error?.message || "Request failed. Please retry.") + details,
      );
    }
    return body as T;
  } catch (error) {
    if (error instanceof RequestError) throw error;
    throw new RequestError(
      "NETWORK_ERROR",
      "Unable to reach the service. Your running job is not cancelled. Please retry.",
    );
  } finally {
    clearTimeout(timeout);
  }
}
export const api = {
  async bootstrap() {
    const result = await request<Bootstrap>("/bootstrap");
    csrf = result.csrf_token;
    return result;
  },
  health: () =>
    request<{ status: string; services: Record<string, boolean> }>("/health"),
  connections: () => request<{ connections: Connection[] }>("/s3/connections"),
  connect: (body: Record<string, string>) =>
    request<Connection>("/s3/connections", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  disconnect: (id: string) =>
    request<void>(`/s3/connections/${id}`, { method: "DELETE" }),
  files: (id: string, prefix: string, cursor = "") =>
    request<{ files: SourceFile[]; next_cursor: string | null }>(
      `/s3/connections/${id}/files?prefix=${encodeURIComponent(prefix)}&cursor=${encodeURIComponent(cursor)}`,
    ),
  inspect: (body: Record<string, unknown>) =>
    request<Job>("/files/inspect", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }),
  createJob: (body: Record<string, unknown>, key: string) =>
    request<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Idempotency-Key": key },
    }),
  jobs: () => request<{ jobs: Job[] }>("/jobs"),
  job: (id: string) => request<Job>(`/jobs/${id}`),
  cancel: (id: string) =>
    request<Job>(`/jobs/${id}/cancel`, { method: "POST" }),
  results: (id: string, cursor: string, limit: number) =>
    request<ResultPage>(
      `/jobs/${id}/results?cursor=${encodeURIComponent(cursor)}&limit=${limit}`,
    ),
};
