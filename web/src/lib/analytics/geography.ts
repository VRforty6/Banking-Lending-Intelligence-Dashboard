import { z } from "zod";

import { STATES, YEARS } from "./constants";

export const GEOGRAPHY_METRICS = [
  "applicationVolume",
  "originationRate",
  "denialRate",
] as const;

export type GeographyMetric = (typeof GEOGRAPHY_METRICS)[number];

export interface GeographyFilters {
  year: number | null;
  state: string | null;
  county: string | null;
  lender: string | null;
  metric: GeographyMetric;
}

export interface GeographyMetrics {
  totalHmdaRecords: number;
  applicationVolume: number;
  creditDecisions: number;
  originations: number;
  denials: number;
  originationRate: number | null;
  denialRate: number | null;
}

export interface GeographyRow extends GeographyMetrics {
  code: string;
  state: string;
  name: string;
  level: "state" | "county";
  mapped: boolean;
}

export interface GeographyObservation {
  id: string;
  label: string;
  detail: string;
}

export interface GeographyData {
  hasData: boolean;
  filters: GeographyFilters;
  scope: {
    level: "national" | "state" | "county";
    code: string;
    name: string;
  };
  parentScope: {
    level: "national" | "state";
    code: string;
    name: string;
  } | null;
  metrics: GeographyMetrics;
  parentMetrics: GeographyMetrics | null;
  rows: GeographyRow[];
  observations: GeographyObservation[];
  options: {
    years: number[];
    states: Array<{ value: string; label: string; fips: string }>;
    selectedLender: { lei: string; label: string } | null;
  };
  refreshedAt: string;
}

const stateValues = STATES.map((state) => state.value);
const yearValues = YEARS.map(String);

const optionalAllowed = (allowed: readonly string[], label: string) =>
  z
    .string()
    .trim()
    .default("all")
    .refine((value) => value === "all" || allowed.includes(value), {
      message: `Invalid ${label}`,
    });

export const geographyFilterSchema = z
  .object({
    year: optionalAllowed(yearValues, "year"),
    state: optionalAllowed(stateValues, "state"),
    county: z
      .string()
      .trim()
      .default("all")
      .refine(
        (value) => value === "all" || value === "UNKNOWN" || /^\d{5}$/.test(value),
        { message: "Invalid county" },
      ),
    lender: z
      .string()
      .trim()
      .default("all")
      .refine(
        (value) => value === "all" || /^[A-Z0-9]{20}$/.test(value),
        { message: "Invalid lender" },
      ),
    metric: z.enum(GEOGRAPHY_METRICS).default("applicationVolume"),
  })
  .superRefine((value, context) => {
    if (value.county !== "all" && value.state === "all") {
      context.addIssue({
        code: "custom",
        path: ["county"],
        message: "A county requires a state",
      });
    }
  });

export function parseGeographyFilters(
  searchParams: URLSearchParams,
): GeographyFilters {
  const state = searchParams.get("state") ?? "all";
  const lender = searchParams.get("lender") ?? "all";
  const parsed = geographyFilterSchema.parse({
    year: searchParams.get("year") ?? "all",
    state: state === "all" ? "all" : state.toUpperCase(),
    county: searchParams.get("county") ?? "all",
    lender: lender === "all" ? "all" : lender.toUpperCase(),
    metric: searchParams.get("metric") ?? "applicationVolume",
  });

  return {
    year: parsed.year === "all" ? null : Number(parsed.year),
    state: parsed.state === "all" ? null : parsed.state,
    county: parsed.county === "all" ? null : parsed.county,
    lender: parsed.lender === "all" ? null : parsed.lender,
    metric: parsed.metric,
  };
}

export function geographyFiltersToQuery(filters: GeographyFilters): string {
  const params = new URLSearchParams();
  if (filters.year !== null) params.set("year", String(filters.year));
  if (filters.state !== null) params.set("state", filters.state);
  if (filters.county !== null) params.set("county", filters.county);
  if (filters.lender !== null) params.set("lender", filters.lender);
  if (filters.metric !== "applicationVolume") params.set("metric", filters.metric);
  return params.toString();
}

export function metricValue(row: GeographyMetrics, metric: GeographyMetric) {
  return row[metric];
}
