# SQL Validation Queries

This document describes the validation queries used to verify the correctness of the ETL process and the resulting data in the PostgreSQL database.

## Validation Queries (06_validation_queries.sql)

The following checks are performed:

### 1. Staging Row Count
Verifies that the number of rows in the staging table matches the expected count from the source Parquet file.
```sql
SELECT COUNT(*) AS staging_row_count FROM staging.hmda_raw;
```
**Expected**: 1,161,292

### 2. Fact Row Count
Ensures that all rows from the staging table were successfully transformed and loaded into the fact table.
```sql
SELECT COUNT(*) AS fact_row_count FROM analytics.fact_loan_application;
```
**Expected**: 1,161,292

### 3. Staging-to-Fact Reconciliation
Confirms that there is a one-to-one mapping between staging rows and fact rows via the `source_row_id` foreign key.
```sql
SELECT
    (SELECT COUNT(*) FROM staging.hmda_raw) AS staging_count,
    (SELECT COUNT(*) FROM analytics.fact_loan_application) AS fact_count,
    (SELECT COUNT(*) FROM staging.hmda_raw s
     LEFT JOIN analytics.fact_loan_application f ON s.stg_row_id = f.source_row_id
     WHERE f.fact_loan_application_key IS NULL) AS unmatched_staging_rows,
    (SELECT COUNT(*) FROM analytics.fact_loan_application f
     LEFT JOIN staging.hmda_raw s ON f.source_row_id = s.stg_row_id
     WHERE s.stg_row_id IS NULL) AS orphaned_fact_rows
```
**Expected**: All counts should be zero except the first two, which should equal 1,161,292.

### 4. Duplicate Source Rows
Checks for duplicate `stg_row_id` values in the fact table, which would indicate duplicate loading.
```sql
SELECT source_row_id, COUNT(*) AS duplicate_count
FROM analytics.fact_loan_application
GROUP BY source_row_id
HAVING COUNT(*) > 1;
```
**Expected**: No results (empty set).

### 5. Null Mandatory Keys
Ensures that no fact row has a null foreign key to any dimension table.
```sql
SELECT
    'lei_key' AS column_name, COUNT(*) AS null_count
FROM analytics.fact_loan_application
WHERE lei_key IS NULL
UNION ALL
SELECT 'geography_key', COUNT(*) FROM analytics.fact_loan_application WHERE geography_key IS NULL
UNION ALL
SELECT 'loan_key', COUNT(*) FROM analytics.fact_loan_application WHERE loan_key IS NULL
UNION ALL
SELECT 'applicant_profile_key', COUNT(*) FROM analytics.fact_loan_application WHERE applicant_profile_key IS NULL
UNION ALL
SELECT 'action_taken_key', COUNT(*) FROM analytics.fact_loan_application WHERE action_taken_key IS NULL;
```
**Expected**: All counts should be zero.

### 6. Invalid Action Codes
Verifies that all action_taken codes in the fact table are valid (1 through 8).
```sql
SELECT
    f.action_taken_key,
    COUNT(*) AS invalid_count
FROM analytics.fact_loan_application f
JOIN analytics.dim_action_taten d ON f.action_taken_key = d.action_taken_key
WHERE d.action_taken NOT IN (1,2,3,4,5,6,7,8)
GROUP BY f.action_taken_key;
```
**Expected**: No results.

### 7. Invalid Loan Amounts
Checks for loan amounts that are null or non-positive (where not null).
```sql
SELECT COUNT(*) AS invalid_loan_amount_count
FROM analytics.fact_loan_application
WHERE loan_amount IS NULL OR loan_amount <= 0;
```
**Expected**: 0 (nulls are allowed, but non-positive values are not).

### 8. Unmatched Dimension Keys
Ensures that all foreign keys in the fact table reference existing rows in the dimension tables.
```sql
SELECT
    'lei' AS table_name, COUNT(*) AS unmatched_count
FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_lender d ON f.lei_key = d.lei_key
WHERE d.lei_key IS NULL
UNION ALL
SELECT 'geography', COUNT(*) FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_geography g ON f.geography_key = g.geography_key
WHERE g.geography_key IS NULL
UNION ALL
SELECT 'loan', COUNT(*) FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_loan l ON f.loan_key = l.loan_key
WHERE l.loan_key IS NULL
UNION ALL
SELECT 'applicant_profile', COUNT(*) FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_applicant_profile a ON f.applicant_profile_key = a.applicant_profile_key
WHERE a.applicant_profile_key IS NULL
UNION ALL
SELECT 'action_taken', COUNT(*) FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_action_taten t ON f.action_taken_key = t.action_taken_key
WHERE t.action_taken_key IS NULL;
```
**Expected**: All counts should be zero.

### 9. Staging-to-Fact Reconciliation (Alternate)
An alternative check that compares the total number of rows in staging and fact, and ensures the difference is zero.
```sql
SELECT
    (SELECT COUNT(*) FROM staging.hmda_raw) -
    (SELECT COUNT(*) FROM analytics.fact_loan_application) AS reconciliation_difference;
```
**Expected**: 0