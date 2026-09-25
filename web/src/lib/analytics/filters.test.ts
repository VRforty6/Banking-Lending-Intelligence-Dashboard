import { describe, expect, it } from "vitest";

import { filtersToQuery, parseExecutiveFilters } from "./filters";

describe("parseExecutiveFilters", () => {
  it("uses the all-population defaults", () => {
    expect(parseExecutiveFilters(new URLSearchParams())).toEqual({
      year: null,
      state: null,
      loanPurpose: null,
    });
  });

  it("accepts the established warehouse filter values", () => {
    expect(
      parseExecutiveFilters(
        new URLSearchParams("year=2025&state=ca&purpose=31"),
      ),
    ).toEqual({ year: 2025, state: "CA", loanPurpose: "31" });
  });

  it.each([
    ["year=2022", "Invalid year"],
    ["state=WA", "Invalid state"],
    ["purpose=99", "Invalid loan purpose"],
    ["year=2025%27%3BDELETE+FROM+analytics.fact_loan_application", "Invalid year"],
  ])("rejects unsupported input %s", (query, expectedMessage) => {
    expect(() => parseExecutiveFilters(new URLSearchParams(query))).toThrow(
      expectedMessage,
    );
  });
});

describe("filtersToQuery", () => {
  it("persists only active filters", () => {
    expect(
      filtersToQuery({ year: 2024, state: null, loanPurpose: "1" }),
    ).toBe("year=2024&purpose=1");
  });
});
