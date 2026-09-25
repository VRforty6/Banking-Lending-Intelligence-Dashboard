-- Exact, bounded aggregates for the interactive web analytics application.
--
-- These materialized views preserve the Power BI reporting populations in
-- docs/POWER_BI_REPORTING_LOGIC.md. They do not change the warehouse grain or
-- the established ETL. Refresh them after a successful warehouse refresh:
--
--   REFRESH MATERIALIZED VIEW analytics.mv_web_executive_metrics;
--   REFRESH MATERIALIZED VIEW analytics.mv_web_county_volume;
--   REFRESH MATERIALIZED VIEW analytics.mv_web_lender_volume;

DROP MATERIALIZED VIEW IF EXISTS analytics.mv_web_executive_metrics;

CREATE MATERIALIZED VIEW analytics.mv_web_executive_metrics AS
WITH executive_source AS (
    SELECT
        f.application_year,
        g.state_code,
        ln.loan_purpose,
        a.action_taken,
        f.loan_amount,
        f.income
    FROM analytics.fact_loan_application f
    JOIN analytics.dim_geography g
      ON g.geography_key = f.geography_key
    JOIN analytics.dim_loan ln
      ON ln.loan_key = f.loan_key
    JOIN analytics.dim_action_taken a
      ON a.action_taken_key = f.action_taken_key
)
SELECT
    CASE WHEN GROUPING(application_year) = 1 THEN 0 ELSE application_year END AS application_year,
    CASE WHEN GROUPING(state_code) = 1 THEN 'ALL' ELSE state_code END AS state_code,
    CASE WHEN GROUPING(loan_purpose) = 1 THEN 'ALL' ELSE loan_purpose END AS loan_purpose,
    COUNT(*)::bigint AS total_hmda_records,
    COUNT(*) FILTER (WHERE action_taken <> 6)::bigint AS application_volume,
    COUNT(*) FILTER (WHERE action_taken IN (1, 2, 3))::bigint AS credit_decisions,
    COUNT(*) FILTER (WHERE action_taken = 1)::bigint AS originations,
    COUNT(*) FILTER (WHERE action_taken = 2)::bigint AS approved_not_accepted,
    COUNT(*) FILTER (WHERE action_taken = 3)::bigint AS denials,
    COUNT(*) FILTER (WHERE action_taken = 4)::bigint AS withdrawals,
    COUNT(*) FILTER (WHERE action_taken = 5)::bigint AS incomplete,
    COUNT(*) FILTER (WHERE action_taken = 6)::bigint AS purchased_loans,
    COUNT(*) FILTER (WHERE action_taken = 7)::bigint AS preapproval_denied,
    COUNT(*) FILTER (WHERE action_taken = 8)::bigint AS preapproval_approved_not_accepted,
    SUM(loan_amount) FILTER (WHERE action_taken = 1) AS originated_loan_amount_sum,
    COUNT(loan_amount) FILTER (WHERE action_taken = 1)::bigint AS originated_loan_amount_count,
    AVG(income) AS average_applicant_income,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY income) AS median_applicant_income,
    CURRENT_TIMESTAMP AS refreshed_at
FROM executive_source
GROUP BY CUBE (application_year, state_code, loan_purpose);

CREATE UNIQUE INDEX mv_web_executive_metrics_scope_uq
    ON analytics.mv_web_executive_metrics (application_year, state_code, loan_purpose);

DROP MATERIALIZED VIEW IF EXISTS analytics.mv_web_county_volume;

CREATE MATERIALIZED VIEW analytics.mv_web_county_volume AS
SELECT
    f.application_year,
    g.state_code,
    g.county_code,
    ln.loan_purpose,
    COUNT(*) FILTER (WHERE a.action_taken <> 6)::bigint AS application_volume,
    CURRENT_TIMESTAMP AS refreshed_at
FROM analytics.fact_loan_application f
JOIN analytics.dim_geography g
  ON g.geography_key = f.geography_key
JOIN analytics.dim_loan ln
  ON ln.loan_key = f.loan_key
JOIN analytics.dim_action_taken a
  ON a.action_taken_key = f.action_taken_key
GROUP BY f.application_year, g.state_code, g.county_code, ln.loan_purpose;

CREATE UNIQUE INDEX mv_web_county_volume_scope_uq
    ON analytics.mv_web_county_volume (
        application_year,
        state_code,
        county_code,
        loan_purpose
    );

CREATE INDEX mv_web_county_volume_filters_idx
    ON analytics.mv_web_county_volume (application_year, state_code, loan_purpose);

DROP MATERIALIZED VIEW IF EXISTS analytics.mv_web_lender_volume;

CREATE MATERIALIZED VIEW analytics.mv_web_lender_volume AS
SELECT
    f.application_year,
    g.state_code,
    ln.loan_purpose,
    l.lei,
    l.lender_name,
    COUNT(*) FILTER (WHERE a.action_taken <> 6)::bigint AS application_volume,
    CURRENT_TIMESTAMP AS refreshed_at
FROM analytics.fact_loan_application f
JOIN analytics.dim_geography g
  ON g.geography_key = f.geography_key
JOIN analytics.dim_loan ln
  ON ln.loan_key = f.loan_key
JOIN analytics.dim_lender l
  ON l.lei_key = f.lei_key
JOIN analytics.dim_action_taken a
  ON a.action_taken_key = f.action_taken_key
GROUP BY f.application_year, g.state_code, ln.loan_purpose, l.lei, l.lender_name;

CREATE UNIQUE INDEX mv_web_lender_volume_scope_uq
    ON analytics.mv_web_lender_volume (
        application_year,
        state_code,
        loan_purpose,
        lei
    );

CREATE INDEX mv_web_lender_volume_filters_idx
    ON analytics.mv_web_lender_volume (application_year, state_code, loan_purpose);
