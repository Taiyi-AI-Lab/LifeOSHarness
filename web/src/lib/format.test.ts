import { describe, expect, it } from "vitest";

import { countByStatus, formatMillis } from "./format";

describe("formatMillis", () => {
  it("formats millisecond timestamps for console tables", () => {
    expect(formatMillis(1_717_200_000_000)).toContain("2024");
    expect(formatMillis(null)).toBe("never");
  });
});

describe("countByStatus", () => {
  it("counts items by status with a stable unknown fallback", () => {
    expect(countByStatus([{ status: "active" }, { status: "gone" }, {}])).toEqual({
      active: 1,
      gone: 1,
      unknown: 1,
    });
  });
});
