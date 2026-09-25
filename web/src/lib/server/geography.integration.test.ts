import { afterAll, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import type { GeographyFilters, GeographyMetrics } from "../analytics/geography";
import { fetchGeographyData } from "./geography";
import { getDatabasePool } from "./db";

const enabled = process.env.RUN_DB_INTEGRATION_TESTS === "true";
const base: GeographyFilters = { year: null, state: null, county: null, lender: null, metric: "applicationVolume" };

async function rawMetrics(filters: GeographyFilters): Promise<GeographyMetrics> {
  const client = await getDatabasePool().connect();
  await client.query("SET statement_timeout = '120s'");
  try {
  const result = await client.query<{
    total_hmda_records: string; application_volume: string; credit_decisions: string; originations: string; denials: string;
  }>(`
    SELECT
      COUNT(*)::bigint AS total_hmda_records,
      COUNT(*) FILTER (WHERE a.action_taken <> 6)::bigint AS application_volume,
      COUNT(*) FILTER (WHERE a.action_taken IN (1, 2, 3))::bigint AS credit_decisions,
      COUNT(*) FILTER (WHERE a.action_taken = 1)::bigint AS originations,
      COUNT(*) FILTER (WHERE a.action_taken = 3)::bigint AS denials
    FROM analytics.fact_loan_application f
    JOIN analytics.dim_geography g ON g.geography_key = f.geography_key
    JOIN analytics.dim_lender l ON l.lei_key = f.lei_key
    JOIN analytics.dim_action_taken a ON a.action_taken_key = f.action_taken_key
    WHERE ($1::bigint IS NULL OR f.application_year = $1)
      AND ($2::text IS NULL OR g.state_code = $2)
      AND ($3::text IS NULL OR g.county_code = $3)
      AND ($4::text IS NULL OR l.lei = $4)`, [filters.year, filters.state, filters.county, filters.lender]);
  const row = result.rows[0];
  const creditDecisions = Number(row.credit_decisions);
  const originations = Number(row.originations);
  const denials = Number(row.denials);
  return {
    totalHmdaRecords: Number(row.total_hmda_records),
    applicationVolume: Number(row.application_volume),
    creditDecisions,
    originations,
    denials,
    originationRate: creditDecisions ? originations / creditDecisions : null,
    denialRate: creditDecisions ? denials / creditDecisions : null,
  };
  } finally {
    client.release();
  }
}

describe.skipIf(!enabled)("geography PostgreSQL reconciliation", () => {
  afterAll(async () => getDatabasePool().end());

  it.each([
    ["overall multi-year", base],
    ["California 2025", { ...base, year: 2025, state: "CA" }],
    ["Texas 2024", { ...base, year: 2024, state: "TX" }],
    ["Los Angeles County 2025", { ...base, year: 2025, state: "CA", county: "06037" }],
    ["lender filtered", { ...base, lender: "549300FGXN1K3HLB1R50" }],
  ] as const)("matches raw facts for %s", async (_label, filters) => {
    const [api, raw] = await Promise.all([fetchGeographyData(filters), rawMetrics(filters)]);
    expect(api.metrics).toEqual(raw);
    if (filters.county === "06037") expect(api.scope.name).toBe("Los Angeles County");
  }, 120_000);
});
