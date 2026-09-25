import { describe, expect, it } from "vitest";

import {
  geographyFiltersToQuery,
  parseGeographyFilters,
} from "./geography";

describe("geography filters", () => {
  it("uses the national all-years volume view by default", () => {
    expect(parseGeographyFilters(new URLSearchParams())).toEqual({
      year: null,
      state: null,
      county: null,
      lender: null,
      metric: "applicationVolume",
    });
  });

  it("parses a deep-linked county and lender scope", () => {
    const filters = parseGeographyFilters(
      new URLSearchParams(
        "year=2025&state=ca&county=06037&lender=549300FGXN1K3HLB1R50&metric=denialRate",
      ),
    );
    expect(filters).toEqual({
      year: 2025,
      state: "CA",
      county: "06037",
      lender: "549300FGXN1K3HLB1R50",
      metric: "denialRate",
    });
    expect(geographyFiltersToQuery(filters)).toBe(
      "year=2025&state=CA&county=06037&lender=549300FGXN1K3HLB1R50&metric=denialRate",
    );
  });

  it("requires a state when a county is supplied", () => {
    expect(() =>
      parseGeographyFilters(new URLSearchParams("county=06037")),
    ).toThrow("A county requires a state");
  });

  it.each([
    "year=2022",
    "state=CA%27%20OR%201%3D1--",
    "county=0603",
    "lender=DROP%20TABLE",
    "metric=averageLoanAmount",
  ])("rejects invalid input: %s", (query) => {
    expect(() => parseGeographyFilters(new URLSearchParams(query))).toThrow();
  });
});
