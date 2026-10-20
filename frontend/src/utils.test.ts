import { describe, expect, it } from "vitest";
import {
  filename,
  formatBytes,
  durationLabel,
  resultExpired,
  operationLabel,
  dateLabel,
} from "./utils";
import type { Job } from "./api";

describe("file presentation", () => {
  it("keeps useful units for small and large data", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1024 ** 3 * 2)).toBe("2.0 GB");
  });
  it("preserves unicode and spaces in object names", () => {
    expect(filename("客户/October export.csv")).toBe("October export.csv");
  });
});

describe("real job presentation", () => {
  const job = {
    kind: "transform",
    status: "SUCCESS",
    result_available: true,
    result_expires_at: "2026-10-21T00:00:00Z",
    started_at: "2026-10-20T00:00:00Z",
    finished_at: "2026-10-20T00:01:05Z",
  } as Job;
  it("retains succeeded status when results expire", () => {
    expect(resultExpired(job, Date.parse("2026-10-22T00:00:00Z"))).toBe(true);
    expect(
      resultExpired(
        { ...job, status: "FAILED" },
        Date.parse("2026-10-22T00:00:00Z"),
      ),
    ).toBe(false);
    expect(resultExpired(job, Date.parse("2026-10-20T00:00:00Z"))).toBe(false);
    expect(resultExpired({ ...job, result_available: false }, 0)).toBe(true);
  });
  it("formats recorded duration and operation without invented values", () => {
    expect(durationLabel(job)).toBe("1m 5s");
    expect(durationLabel({ ...job, started_at: null })).toBe("—");
    expect(operationLabel("regex_extract")).toBe("Extract values");
    expect(operationLabel(undefined)).toBe("File inspection");
  });
  it("uses the explicit Sydney timezone across browsers", () => {
    expect(dateLabel("2026-10-20T00:00:00Z")).toContain("11:00");
  });
});
