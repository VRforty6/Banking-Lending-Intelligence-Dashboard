import { z } from "zod";

import { LOAN_PURPOSES, STATES, YEARS } from "./constants";
import type { ExecutiveFilters } from "./types";

const yearValues = YEARS.map(String);
const stateValues = STATES.map((state) => state.value);
const loanPurposeValues = LOAN_PURPOSES.map((purpose) => purpose.value);

const allOr = (allowed: readonly string[], label: string) =>
  z
    .string()
    .trim()
    .default("all")
    .refine((value) => value === "all" || allowed.includes(value), {
      message: `Invalid ${label}`,
    });

export const executiveFilterSchema = z.object({
  year: allOr(yearValues, "year"),
  state: allOr(stateValues, "state"),
  purpose: allOr(loanPurposeValues, "loan purpose"),
});

export function parseExecutiveFilters(
  searchParams: URLSearchParams,
): ExecutiveFilters {
  const rawState = searchParams.get("state") ?? "all";
  const parsed = executiveFilterSchema.parse({
    year: searchParams.get("year") ?? "all",
    state: rawState === "all" ? "all" : rawState.toUpperCase(),
    purpose: searchParams.get("purpose") ?? "all",
  });

  return {
    year: parsed.year === "all" ? null : Number(parsed.year),
    state: parsed.state === "all" ? null : parsed.state,
    loanPurpose: parsed.purpose === "all" ? null : parsed.purpose,
  };
}

export function filtersToQuery(filters: ExecutiveFilters): string {
  const params = new URLSearchParams();
  if (filters.year !== null) params.set("year", String(filters.year));
  if (filters.state !== null) params.set("state", filters.state);
  if (filters.loanPurpose !== null) params.set("purpose", filters.loanPurpose);
  return params.toString();
}
