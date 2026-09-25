-- Phase 2A county-name reference and exact geographic aggregates.
-- This is additive: it does not alter warehouse facts, dimensions, ETL, or
-- Power BI objects.

CREATE TABLE IF NOT EXISTS analytics.ref_county (
    county_fips TEXT PRIMARY KEY,
    state_code TEXT NOT NULL,
    county_name TEXT NOT NULL,
    internal_latitude DOUBLE PRECISION NOT NULL,
    internal_longitude DOUBLE PRECISION NOT NULL,
    source_vintage INTEGER NOT NULL,
    CONSTRAINT ref_county_fips_format CHECK (county_fips ~ '^[0-9]{5}$'),
    CONSTRAINT ref_county_state_format CHECK (state_code ~ '^[A-Z]{2}$')
);

CREATE INDEX IF NOT EXISTS ref_county_state_idx
    ON analytics.ref_county (state_code, county_fips);

-- Load sql/generated/10_county_reference_seed.sql after creating the table,
-- then execute the materialized-view statements below.

DROP MATERIALIZED VIEW IF EXISTS analytics.mv_web_geography_metrics;

CREATE MATERIALIZED VIEW analytics.mv_web_geography_metrics AS
SELECT
    f.application_year,
    g.state_code,
    g.county_code,
    l.lei,
    COUNT(*)::bigint AS total_hmda_records,
    COUNT(*) FILTER (WHERE a.action_taken <> 6)::bigint AS application_volume,
    COUNT(*) FILTER (WHERE a.action_taken IN (1, 2, 3))::bigint AS credit_decisions,
    COUNT(*) FILTER (WHERE a.action_taken = 1)::bigint AS originations,
    COUNT(*) FILTER (WHERE a.action_taken = 3)::bigint AS denials,
    CURRENT_TIMESTAMP AS refreshed_at
FROM analytics.fact_loan_application f
JOIN analytics.dim_geography g
  ON g.geography_key = f.geography_key
JOIN analytics.dim_lender l
  ON l.lei_key = f.lei_key
JOIN analytics.dim_action_taken a
  ON a.action_taken_key = f.action_taken_key
GROUP BY f.application_year, g.state_code, g.county_code, l.lei;

CREATE UNIQUE INDEX mv_web_geography_metrics_grain_uq
    ON analytics.mv_web_geography_metrics (
        application_year,
        state_code,
        county_code,
        lei
    );

CREATE INDEX mv_web_geography_metrics_scope_idx
    ON analytics.mv_web_geography_metrics (
        application_year,
        state_code,
        county_code
    );

CREATE INDEX mv_web_geography_metrics_lender_scope_idx
    ON analytics.mv_web_geography_metrics (
        lei,
        application_year,
        state_code,
        county_code
    );

-- Refresh after a successful warehouse refresh:
--   REFRESH MATERIALIZED VIEW analytics.mv_web_geography_metrics;
