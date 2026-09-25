import "server-only";

import {
  ACTION_LABELS,
  LOAN_PURPOSES,
  METRIC_DEFINITIONS,
  STATES,
  YEARS,
} from "@/lib/analytics/constants";
import type {
  ExecutiveData,
  ExecutiveFilters,
} from "@/lib/analytics/types";

import { getDatabasePool } from "./db";

type DatabaseNumber = number | string | null;

interface MetricRow {
  application_year: DatabaseNumber;
  state_code: string;
  loan_purpose: string;
  total_hmda_records: DatabaseNumber;
  application_volume: DatabaseNumber;
  credit_decisions: DatabaseNumber;
  originations: DatabaseNumber;
  approved_not_accepted: DatabaseNumber;
  denials: DatabaseNumber;
  withdrawals: DatabaseNumber;
  incomplete: DatabaseNumber;
  purchased_loans: DatabaseNumber;
  preapproval_denied: DatabaseNumber;
  preapproval_approved_not_accepted: DatabaseNumber;
  originated_loan_amount_sum: DatabaseNumber;
  originated_loan_amount_count: DatabaseNumber;
  average_applicant_income: DatabaseNumber;
  median_applicant_income: DatabaseNumber;
  refreshed_at: Date | string;
}

const numberValue = (value: DatabaseNumber): number =>
  value === null ? 0 : Number(value);

const nullableRate = (numerator: number, denominator: number): number | null =>
  denominator === 0 ? null : numerator / denominator;

const metricParameters = (filters: ExecutiveFilters) => [
  filters.year ?? 0,
  filters.state ?? "ALL",
  filters.loanPurpose ?? "ALL",
];

const detailParameters = (filters: ExecutiveFilters) => [
  filters.year,
  filters.state,
  filters.loanPurpose,
];

export async function fetchExecutiveData(
  filters: ExecutiveFilters,
): Promise<ExecutiveData> {
  const pool = getDatabasePool();

  const [metricResult, trendResult, purposeResult, stateResult, lenderResult, countyResult, refreshResult] =
    await Promise.all([
      pool.query<MetricRow>(
        `SELECT *
         FROM analytics.mv_web_executive_metrics
         WHERE application_year = $1
           AND state_code = $2
           AND loan_purpose = $3`,
        metricParameters(filters),
      ),
      pool.query<MetricRow>(
        `SELECT *
         FROM analytics.mv_web_executive_metrics
         WHERE application_year <> 0
           AND state_code = $1
           AND loan_purpose = $2
           AND ($3::bigint IS NULL OR application_year = $3)
         ORDER BY application_year`,
        [filters.state ?? "ALL", filters.loanPurpose ?? "ALL", filters.year],
      ),
      pool.query<MetricRow>(
        `SELECT *
         FROM analytics.mv_web_executive_metrics
         WHERE application_year = $1
           AND state_code = $2
           AND loan_purpose <> 'ALL'
           AND ($3::text IS NULL OR loan_purpose = $3)
         ORDER BY application_volume DESC, loan_purpose`,
        [filters.year ?? 0, filters.state ?? "ALL", filters.loanPurpose],
      ),
      pool.query<MetricRow>(
        `SELECT *
         FROM analytics.mv_web_executive_metrics
         WHERE application_year = $1
           AND state_code <> 'ALL'
           AND loan_purpose = $2
           AND ($3::text IS NULL OR state_code = $3)
         ORDER BY application_volume DESC, state_code`,
        [filters.year ?? 0, filters.loanPurpose ?? "ALL", filters.state],
      ),
      pool.query<{
        lei: string;
        lender_label: string;
        application_volume: DatabaseNumber;
      }>(
        `WITH lender_name_counts AS (
           SELECT TRIM(lender_name) AS lender_name, COUNT(*)::bigint AS name_count
           FROM analytics.dim_lender
           WHERE lender_name IS NOT NULL AND TRIM(lender_name) <> ''
           GROUP BY TRIM(lender_name)
         ), ranked AS (
           SELECT
             mv.lei,
             CASE
               WHEN mv.lender_name IS NULL OR TRIM(mv.lender_name) = '' THEN mv.lei
               WHEN counts.name_count > 1
                 THEN TRIM(mv.lender_name) || ' (' || RIGHT(mv.lei, 6) || ')'
               ELSE TRIM(mv.lender_name)
             END AS lender_label,
             SUM(mv.application_volume)::bigint AS application_volume
           FROM analytics.mv_web_lender_volume mv
           LEFT JOIN lender_name_counts counts
             ON counts.lender_name = TRIM(mv.lender_name)
           WHERE ($1::bigint IS NULL OR mv.application_year = $1)
             AND ($2::text IS NULL OR mv.state_code = $2)
             AND ($3::text IS NULL OR mv.loan_purpose = $3)
           GROUP BY mv.lei, mv.lender_name, counts.name_count
         )
         SELECT lei, lender_label, application_volume
         FROM ranked
         WHERE application_volume > 0
         ORDER BY application_volume DESC, lei
         LIMIT 8`,
        detailParameters(filters),
      ),
      pool.query<{
        state_code: string;
        county_code: string;
        application_volume: DatabaseNumber;
      }>(
        `SELECT
           state_code,
           county_code,
           SUM(application_volume)::bigint AS application_volume
         FROM analytics.mv_web_county_volume
         WHERE ($1::bigint IS NULL OR application_year = $1)
           AND ($2::text IS NULL OR state_code = $2)
           AND ($3::text IS NULL OR loan_purpose = $3)
         GROUP BY state_code, county_code
         HAVING SUM(application_volume) > 0
         ORDER BY application_volume DESC, state_code, county_code
         LIMIT 8`,
        detailParameters(filters),
      ),
      pool.query<{ refreshed_at: Date | string }>(
        `SELECT MAX(refreshed_at) AS refreshed_at
         FROM analytics.mv_web_executive_metrics`,
      ),
    ]);

  const metric = metricResult.rows[0];
  if (!metric) {
    const refreshedAt = refreshResult.rows[0]?.refreshed_at;
    return {
      hasData: false,
      filters,
      options: {
        years: [...YEARS],
        states: STATES.map((state) => ({ ...state })),
        loanPurposes: LOAN_PURPOSES.map((purpose) => ({ ...purpose })),
      },
      kpis: {
        applicationVolume: { value: null },
        originationRate: { value: null },
        denialRate: { value: null },
        averageOriginatedLoanAmount: { value: null },
        medianApplicantIncome: { value: null },
      },
      context: {
        totalHmdaRecords: 0,
        creditDecisions: 0,
        purchasedLoans: 0,
        refreshedAt: refreshedAt
          ? new Date(refreshedAt).toISOString()
          : new Date(0).toISOString(),
      },
      trend: [],
      outcomes: [],
      loanPurposes: [],
      states: [],
      topLenders: [],
      topCounties: [],
      definitions: METRIC_DEFINITIONS.map((definition) => ({ ...definition })),
    };
  }

  const applicationVolume = numberValue(metric.application_volume);
  const creditDecisions = numberValue(metric.credit_decisions);
  const originations = numberValue(metric.originations);
  const denials = numberValue(metric.denials);
  const originatedAmountCount = numberValue(metric.originated_loan_amount_count);
  const originatedAmountSum = numberValue(metric.originated_loan_amount_sum);

  const outcomes = [
    metric.originations,
    metric.approved_not_accepted,
    metric.denials,
    metric.withdrawals,
    metric.incomplete,
    metric.purchased_loans,
    metric.preapproval_denied,
    metric.preapproval_approved_not_accepted,
  ].map((value, index) => ({
    code: index + 1,
    label: ACTION_LABELS[index + 1],
    value: numberValue(value),
  }));

  return {
    hasData: true,
    filters,
    options: {
      years: [...YEARS],
      states: STATES.map((state) => ({ ...state })),
      loanPurposes: LOAN_PURPOSES.map((purpose) => ({ ...purpose })),
    },
    kpis: {
      applicationVolume: { value: applicationVolume },
      originationRate: {
        value: nullableRate(originations, creditDecisions),
        numerator: originations,
        denominator: creditDecisions,
      },
      denialRate: {
        value: nullableRate(denials, creditDecisions),
        numerator: denials,
        denominator: creditDecisions,
      },
      averageOriginatedLoanAmount: {
        value:
          originatedAmountCount === 0
            ? null
            : originatedAmountSum / originatedAmountCount,
        numerator: originatedAmountSum,
        denominator: originatedAmountCount,
      },
      medianApplicantIncome: {
        value:
          metric.median_applicant_income === null
            ? null
            : Number(metric.median_applicant_income),
      },
    },
    context: {
      totalHmdaRecords: numberValue(metric.total_hmda_records),
      creditDecisions,
      purchasedLoans: numberValue(metric.purchased_loans),
      refreshedAt: new Date(metric.refreshed_at).toISOString(),
    },
    trend: trendResult.rows.map((row) => {
      const rowCreditDecisions = numberValue(row.credit_decisions);
      const rowOriginations = numberValue(row.originations);
      const rowDenials = numberValue(row.denials);
      return {
        year: numberValue(row.application_year),
        applicationVolume: numberValue(row.application_volume),
        originations: rowOriginations,
        denials: rowDenials,
        creditDecisions: rowCreditDecisions,
        originationRate: nullableRate(rowOriginations, rowCreditDecisions),
        denialRate: nullableRate(rowDenials, rowCreditDecisions),
      };
    }),
    outcomes,
    loanPurposes: purposeResult.rows.map((row) => ({
      code: row.loan_purpose,
      label:
        LOAN_PURPOSES.find((purpose) => purpose.value === row.loan_purpose)
          ?.label ?? "Unknown",
      value: numberValue(row.application_volume),
    })),
    states: stateResult.rows.map((row) => {
      const rowCreditDecisions = numberValue(row.credit_decisions);
      const rowOriginations = numberValue(row.originations);
      const rowDenials = numberValue(row.denials);
      return {
        code: row.state_code,
        label:
          STATES.find((state) => state.value === row.state_code)?.label ??
          row.state_code,
        applicationVolume: numberValue(row.application_volume),
        originationRate: nullableRate(rowOriginations, rowCreditDecisions),
        denialRate: nullableRate(rowDenials, rowCreditDecisions),
      };
    }),
    topLenders: lenderResult.rows.map((row) => ({
      lei: row.lei,
      label: row.lender_label,
      applicationVolume: numberValue(row.application_volume),
    })),
    topCounties: countyResult.rows.map((row) => ({
      state: row.state_code,
      county: row.county_code,
      label:
        !row.county_code || row.county_code.toUpperCase() === "UNKNOWN"
          ? "Unknown county"
          : `${row.state_code} · ${row.county_code}`,
      applicationVolume: numberValue(row.application_volume),
    })),
    definitions: METRIC_DEFINITIONS.map((definition) => ({ ...definition })),
  };
}
