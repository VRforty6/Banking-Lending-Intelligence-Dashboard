-- Business Queries for HMDA Analysis

-- 1. Total Applications
SELECT COUNT(*) AS total_applications
FROM analytics.fact_loan_application;

-- 2. Originations (action_taken = 1: Loan originated)
SELECT COUNT(*) AS originations
FROM analytics.fact_loan_application f
JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
WHERE d.action_taken = 1;

-- 3. Approvals (same as originations in HMDA context)
SELECT COUNT(*) AS approvals
FROM analytics.fact_loan_application f
JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
WHERE d.action_taken = 1;

-- 4. Denials (action_taken = 3: Application denied by financial institution)
SELECT COUNT(*) AS denials
FROM analytics.fact_loan_application f
JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
WHERE d.action_taken = 3;

-- 5. Approval Rate (approvals / total applications)
SELECT
    (SELECT COUNT(*)
     FROM analytics.fact_loan_application f
     JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
     WHERE d.action_taken = 1) * 1.0 /
    (SELECT COUNT(*) FROM analytics.fact_loan_application) AS approval_rate;

-- 6. Denial Rate (denials / total applications)
SELECT
    (SELECT COUNT(*)
     FROM analytics.fact_loan_application f
     JOIN analytics.dim_action_taken d ON f.action_taken_key = d.action_taken_key
     WHERE d.action_taken = 3) * 1.0 /
    (SELECT COUNT(*) FROM analytics.fact_loan_application) AS denial_rate;

-- 7. Average Loan Amount
SELECT AVG(loan_amount) AS average_loan_amount
FROM analytics.fact_loan_application
WHERE loan_amount IS NOT NULL;

-- 8. Median Applicant Income
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY income) AS median_income
FROM analytics.fact_loan_application
WHERE income IS NOT NULL;

-- 9. Applications by County
SELECT
    g.county_code,
    COUNT(*) AS application_count
FROM analytics.fact_loan_application f
JOIN analytics.dim_geography g ON f.geography_key = g.geography_key
GROUP BY g.county_code
ORDER BY application_count DESC
LIMIT 20;

-- 10. Applications by Lender (Top 20 Lenders by Application Volume)
SELECT
    l.lei,
    COUNT(*) AS application_count
FROM analytics.fact_loan_application f
JOIN analytics.dim_lender l ON f.lei_key = l.lei_key
GROUP BY l.lei
ORDER BY application_count DESC
LIMIT 20;

-- 11. Loan Purpose Mix
SELECT
    l.loan_purpose,
    COUNT(*) AS application_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage
FROM analytics.fact_loan_application f
JOIN analytics.dim_loan l ON f.loan_key = l.loan_key
GROUP BY l.loan_purpose
ORDER BY application_count DESC;

-- 12. Property Type Mix (using occupancy_type as a proxy)
SELECT
    s.occupancy_type,
    COUNT(*) AS application_count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage
FROM analytics.fact_loan_application f
JOIN staging.hmda_raw s ON f.source_row_id = s.stg_row_id
GROUP BY s.occupancy_type
ORDER BY application_count DESC;

-- 13. Top Denial Reasons
-- Note: Denial reasons are not included in the current model.
-- To include them, we would need to add denial_reason_1 through denial_reason_4
-- to the fact table or create a junk dimension for denial reasons.
-- This query is a placeholder and will need to be updated once the model includes denial reasons.
SELECT
    'DENIAL_REASON_1' AS denial_reason,
    COUNT(*) AS count
FROM staging.hmda_raw
WHERE denial_reason_1 IS NOT NULL AND denial_reason_1 != ''
UNION ALL
SELECT
    'DENIAL_REASON_2',
    COUNT(*) AS count
FROM staging.hmda_raw
WHERE denial_reason_2 IS NOT NULL AND denial_reason_2 != ''
UNION ALL
SELECT
    'DENIAL_REASON_3',
    COUNT(*) AS count
FROM staging.hmda_raw
WHERE denial_reason_3 IS NOT NULL AND denial_reason_3 != ''
UNION ALL
SELECT
    'DENIAL_REASON_4',
    COUNT(*) AS count
FROM staging.hmda_raw
WHERE denial_reason_4 IS NOT NULL AND denial_reason_4 != ''
ORDER BY count DESC
LIMIT 10;