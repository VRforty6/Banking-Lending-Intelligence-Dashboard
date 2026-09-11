SELECT
    'Staging row count' AS check,
    (SELECT COUNT(*) FROM staging.hmda_raw) AS actual_count,
    1161292 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM staging.hmda_raw) = 1161292 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Fact row count' AS check,
    (SELECT COUNT(*) FROM analytics.fact_loan_application) AS actual_count,
    1161292 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM analytics.fact_loan_application) = 1161292 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Duplicate source rows in staging' AS check,
    (SELECT COUNT(*) FROM staging.hmda_raw GROUP BY stg_row_id HAVING COUNT(*) > 1) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM staging.hmda_raw GROUP BY stg_row_id HAVING COUNT(*) > 1) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Null mandatory keys in fact' AS check,
    (SELECT COUNT(*) FROM analytics.fact_loan_application
     WHERE lei_key IS NULL OR geography_key IS NULL OR loan_key IS NULL OR applicant_profile_key IS NULL OR action_taken_key IS NULL) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM analytics.fact_loan_application
              WHERE lei_key IS NULL OR geography_key IS NULL OR loan_key IS NULL OR applicant_profile_key IS NULL OR action_taken_key IS NULL) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Invalid action codes in fact' AS check,
    (SELECT COUNT(*) FROM analytics.fact_loan_application f
     JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
     WHERE d.action_taken NOT IN (1,2,3,4,5,6,7,8)) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM analytics.fact_loan_application f
              JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
              WHERE d.action_taken NOT IN (1,2,3,4,5,6,7,8)) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Invalid loan amounts (non-positive) in fact' AS check,
    (SELECT COUNT(*) FROM analytics.fact_loan_application WHERE loan_amount <= 0 AND loan_amount IS NOT NULL) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM analytics.fact_loan_application WHERE loan_amount <= 0 AND loan_amount IS NOT NULL) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Unmatched dimension keys in fact' AS check,
    (SELECT COUNT(*) FROM analytics.fact_loan_application f
     LEFT JOIN analytics.dim_lender l ON f.lei_key = l.lei_key
     LEFT JOIN analytics.dim_geography g ON f.geography_key = g.geography_key
     LEFT JOIN analytics.dim_loan ln ON f.loan_key = ln.loan_key
     LEFT JOIN analytics.dim_applicant_profile a ON f.applicant_profile_key = a.applicant_profile_key
     LEFT JOIN analytics.dim_action_taken t ON f.action_taken_key = t.action_taken_key
     WHERE l.lei_key IS NULL OR g.geography_key IS NULL OR ln.loan_key IS NULL OR a.applicant_profile_key IS NULL OR t.action_taken_key IS NULL) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM analytics.fact_loan_application f
              LEFT JOIN analytics.dim_lender l ON f.lei_key = l.lei_key
              LEFT JOIN analytics.dim_geography g ON f.geography_key = g.geography_key
              LEFT JOIN analytics.dim_loan ln ON f.loan_key = ln.loan_key
              LEFT JOIN analytics.dim_applicant_profile a ON f.applicant_profile_key = a.applicant_profile_key
              LEFT JOIN analytics.dim_action_taken t ON f.action_taken_key = t.action_taken_key
              WHERE l.lei_key IS NULL OR g.geography_key IS NULL OR ln.loan_key IS NULL OR a.applicant_profile_key IS NULL OR t.action_taken_key IS NULL) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
UNION ALL
SELECT
    'Staging-to-fact reconciliation' AS check,
    (SELECT COUNT(*) FROM staging.hmda_raw) - (SELECT COUNT(*) FROM analytics.fact_loan_application) AS actual_count,
    0 AS expected_count,
    CASE WHEN (SELECT COUNT(*) FROM staging.hmda_raw) - (SELECT COUNT(*) FROM analytics.fact_loan_application) = 0 THEN 'PASS' ELSE 'FAIL' END AS status;