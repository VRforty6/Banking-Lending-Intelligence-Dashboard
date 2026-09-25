import { describe, expect, it } from "vitest";

import {
  formatCurrency,
  formatIncome,
  formatMetric,
  formatPercent,
} from "./format";

describe("executive metric formatting", () => {
  it("keeps rates as fractional percentages", () => {
    expect(formatPercent(0.7228901052)).toBe("72.3%");
  });

  it("keeps HMDA income in thousands rather than multiplying it", () => {
    expect(formatIncome(117)).toBe("$117K");
  });

  it("formats originated loan amounts as dollars", () => {
    expect(formatCurrency(414462.1127)).toBe("$414,462");
  });

  it("shows missing metrics without inventing zero", () => {
    expect(formatMetric(null, "percent")).toBe("—");
  });
});
