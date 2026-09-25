import "server-only";

import { STATES, YEARS } from "../analytics/constants";
import type {
  GeographyData,
  GeographyFilters,
  GeographyMetrics,
  GeographyRow,
} from "../analytics/geography";
import { buildGeographyObservations } from "../analytics/geography-observations";

import { getDatabasePool } from "./db";

type DatabaseNumber = number | string | null;

interface MetricRow {
  total_hmda_records: DatabaseNumber;
  application_volume: DatabaseNumber;
  credit_decisions: DatabaseNumber;
  originations: DatabaseNumber;
  denials: DatabaseNumber;
}

interface ComparisonRow extends MetricRow {
  state_code: string;
  geography_code: string;
  geography_name: string;
  mapped: boolean;
}

const numberValue = (value: DatabaseNumber): number =>
  value === null ? 0 : Number(value);

const toMetrics = (row?: MetricRow): GeographyMetrics => {
  const creditDecisions = numberValue(row?.credit_decisions ?? null);
  const originations = numberValue(row?.originations ?? null);
  const denials = numberValue(row?.denials ?? null);
  return {
    totalHmdaRecords: numberValue(row?.total_hmda_records ?? null),
    applicationVolume: numberValue(row?.application_volume ?? null),
    creditDecisions,
    originations,
    denials,
    originationRate:
      creditDecisions === 0 ? null : originations / creditDecisions,
    denialRate: creditDecisions === 0 ? null : denials / creditDecisions,
  };
};

const scopeParameters = (filters: GeographyFilters) => [
  filters.year,
  filters.state,
  filters.county,
  filters.lender,
];

const metricSql = `
  SELECT
    COALESCE(SUM(total_hmda_records), 0)::bigint AS total_hmda_records,
    COALESCE(SUM(application_volume), 0)::bigint AS application_volume,
    COALESCE(SUM(credit_decisions), 0)::bigint AS credit_decisions,
    COALESCE(SUM(originations), 0)::bigint AS originations,
    COALESCE(SUM(denials), 0)::bigint AS denials
  FROM analytics.mv_web_geography_metrics
  WHERE ($1::bigint IS NULL OR application_year = $1)
    AND ($2::text IS NULL OR state_code = $2)
    AND ($3::text IS NULL OR county_code = $3)
    AND ($4::text IS NULL OR lei = $4)`;

function stateName(code: string) {
  return STATES.find((state) => state.value === code)?.label ?? code;
}

function countyName(code: string, officialName: string | null) {
  if (code.toUpperCase() === "UNKNOWN") return "County not reported";
  return officialName ?? `Unmapped county (${code})`;
}

export async function fetchGeographyData(
  filters: GeographyFilters,
): Promise<GeographyData> {
  const pool = getDatabasePool();
  const parentParameters = filters.county
    ? [filters.year, filters.state, null, filters.lender]
    : filters.state
      ? [filters.year, null, null, filters.lender]
      : scopeParameters(filters);

  const comparisonQuery = filters.state
    ? pool.query<ComparisonRow>(
        `SELECT
           mv.state_code,
           mv.county_code AS geography_code,
           CASE
             WHEN UPPER(mv.county_code) = 'UNKNOWN' THEN 'County not reported'
             WHEN ref.county_name IS NULL THEN 'Unmapped county (' || mv.county_code || ')'
             ELSE ref.county_name
           END AS geography_name,
           (ref.county_fips IS NOT NULL) AS mapped,
           SUM(mv.total_hmda_records)::bigint AS total_hmda_records,
           SUM(mv.application_volume)::bigint AS application_volume,
           SUM(mv.credit_decisions)::bigint AS credit_decisions,
           SUM(mv.originations)::bigint AS originations,
           SUM(mv.denials)::bigint AS denials
         FROM analytics.mv_web_geography_metrics mv
         LEFT JOIN analytics.ref_county ref
           ON ref.county_fips = mv.county_code
          AND ref.state_code = mv.state_code
         WHERE ($1::bigint IS NULL OR mv.application_year = $1)
           AND mv.state_code = $2
           AND ($3::text IS NULL OR mv.lei = $3)
         GROUP BY mv.state_code, mv.county_code, ref.county_fips, ref.county_name
         HAVING SUM(mv.application_volume) > 0
         ORDER BY application_volume DESC, geography_code`,
        [filters.year, filters.state, filters.lender],
      )
    : pool.query<ComparisonRow>(
        `SELECT
           mv.state_code,
           state_fips.geography_code,
           state_fips.geography_name,
           TRUE AS mapped,
           SUM(mv.total_hmda_records)::bigint AS total_hmda_records,
           SUM(mv.application_volume)::bigint AS application_volume,
           SUM(mv.credit_decisions)::bigint AS credit_decisions,
           SUM(mv.originations)::bigint AS originations,
           SUM(mv.denials)::bigint AS denials
         FROM analytics.mv_web_geography_metrics mv
         JOIN (VALUES
           ('CA', '06', 'California'),
           ('FL', '12', 'Florida'),
           ('IL', '17', 'Illinois'),
           ('NY', '36', 'New York'),
           ('TX', '48', 'Texas')
         ) AS state_fips(state_code, geography_code, geography_name)
           ON state_fips.state_code = mv.state_code
         WHERE ($1::bigint IS NULL OR mv.application_year = $1)
           AND ($2::text IS NULL OR mv.lei = $2)
         GROUP BY mv.state_code, state_fips.geography_code, state_fips.geography_name
         HAVING SUM(mv.application_volume) > 0
         ORDER BY application_volume DESC, geography_code`,
        [filters.year, filters.lender],
      );

  const [metricResult, parentMetricResult, comparisonResult, lenderResult, refreshResult, countyResult] =
    await Promise.all([
      pool.query<MetricRow>(metricSql, scopeParameters(filters)),
      filters.state || filters.county
        ? pool.query<MetricRow>(metricSql, parentParameters)
        : Promise.resolve({ rows: [] as MetricRow[] }),
      comparisonQuery,
      filters.lender
        ? pool.query<{ lei: string; lender_label: string }>(
            `SELECT
               l.lei,
               COALESCE(NULLIF(TRIM(l.lender_name), ''), l.lei) AS lender_label
             FROM analytics.dim_lender l
             WHERE l.lei = $1`,
            [filters.lender],
          )
        : Promise.resolve({ rows: [] as Array<{ lei: string; lender_label: string }> }),
      pool.query<{ refreshed_at: Date | string }>(
        `SELECT MAX(refreshed_at) AS refreshed_at
         FROM analytics.mv_web_geography_metrics`,
      ),
      filters.county && filters.state
        ? pool.query<{ county_name: string | null }>(
            `SELECT county_name
             FROM analytics.ref_county
             WHERE county_fips = $1 AND state_code = $2`,
            [filters.county, filters.state],
          )
        : Promise.resolve({ rows: [] as Array<{ county_name: string | null }> }),
    ]);

  const metrics = toMetrics(metricResult.rows[0]);
  const parentMetrics =
    filters.state || filters.county ? toMetrics(parentMetricResult.rows[0]) : null;
  const rows: GeographyRow[] = comparisonResult.rows.map((row) => ({
    ...toMetrics(row),
    code: row.geography_code,
    state: row.state_code,
    name: row.geography_name,
    level: filters.state ? "county" : "state",
    mapped: row.mapped,
  }));

  const countyLabel = filters.county
    ? countyName(filters.county, countyResult.rows[0]?.county_name ?? null)
    : null;
  const scope = filters.county
    ? { level: "county" as const, code: filters.county, name: countyLabel! }
    : filters.state
      ? { level: "state" as const, code: filters.state, name: stateName(filters.state) }
      : { level: "national" as const, code: "US", name: "United States" };
  const parentScope = filters.county
    ? { level: "state" as const, code: filters.state!, name: stateName(filters.state!) }
    : filters.state
      ? { level: "national" as const, code: "US", name: "United States" }
      : null;
  return {
    hasData: metrics.totalHmdaRecords > 0,
    filters,
    scope,
    parentScope,
    metrics,
    parentMetrics,
    rows,
    observations: buildGeographyObservations({
      rows,
      selectedCode: filters.county ? filters.county : null,
      selectedName: scope.name,
      selectedMetrics: metrics,
      parentMetrics,
      metric: filters.metric,
    }),
    options: {
      years: [...YEARS],
      states: STATES.map((state) => ({ ...state })),
      selectedLender: lenderResult.rows[0]
        ? {
            lei: lenderResult.rows[0].lei,
            label: lenderResult.rows[0].lender_label,
          }
        : null,
    },
    refreshedAt: new Date(refreshResult.rows[0]?.refreshed_at ?? 0).toISOString(),
  };
}

export async function searchLenders(query: string) {
  const pool = getDatabasePool();
  const result = await pool.query<{
    lei: string;
    lender_label: string;
    application_volume: DatabaseNumber;
  }>(
    `WITH lender_volume AS (
       SELECT lei, SUM(application_volume)::bigint AS application_volume
       FROM analytics.mv_web_geography_metrics
       GROUP BY lei
     )
     SELECT
       l.lei,
       COALESCE(NULLIF(TRIM(l.lender_name), ''), l.lei) AS lender_label,
       volume.application_volume
     FROM analytics.dim_lender l
     JOIN lender_volume volume ON volume.lei = l.lei
     WHERE $1::text = ''
        OR l.lei ILIKE '%' || $1 || '%'
        OR COALESCE(l.lender_name, '') ILIKE '%' || $1 || '%'
     ORDER BY
       CASE
         WHEN UPPER(l.lei) = UPPER($1) THEN 0
         WHEN UPPER(COALESCE(l.lender_name, '')) = UPPER($1) THEN 1
         WHEN COALESCE(l.lender_name, '') ILIKE $1 || '%' THEN 2
         ELSE 3
       END,
       volume.application_volume DESC,
       l.lei
     LIMIT 20`,
    [query],
  );
  return result.rows.map((row) => ({
    lei: row.lei,
    label: row.lender_label,
    applicationVolume: numberValue(row.application_volume),
  }));
}
