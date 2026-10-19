import { describe, expect, it } from "vitest";
import { filename, formatBytes } from "./utils";

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
