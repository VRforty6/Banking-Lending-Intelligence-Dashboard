# HMDA ETL Troubleshooting Guide

## Common Issues and Solutions

### Schema Mismatch Errors

**Symptoms**: 
- `KeyError` when accessing columns in Python code
- Database errors about missing columns or data type mismatches
- ETL process failing during column mapping

**Diagnosis**:
1. Check source CSV header matches expected columns
2. Verify column name cleaning is working correctly (hyphens to underscores)
3. Confirm that all expected columns are present after cleaning
4. Validate data type conversions are appropriate

**Solutions**:
- Ensure `_clean_column_names` function in `src/clean.py` is functioning
- Add schema validation before processing (see Data Quality section below)
- Update column mappings in SQL files to match cleaned names
- Add detailed logging to show which columns are missing

### Performance Issues

**Symptoms**:
- Slow processing of large files (>1M rows)
- High memory usage during processing
- Long database insertion times

**Diagnosis**:
1. Profile the `compute_profile_hash` function - row-wise pandas operations are slow
2. Check if entire dataset is being loaded into memory
3. Verify database insertions are using batch operations
4. Look for missing indexes on join columns

**Solutions**:
1. Replace row-wise hashing with vectorized operations:
   ```python
   # Instead of: df.apply(compute_profile_hash, axis=1)
   # Use: pandas vectorized string operations
   ```
2. Ensure chunked processing is working correctly
3. Use `method='multi'` or `psycopg2.extras.execute_batch` for inserts
4. Add appropriate indexes on foreign key columns

### Database Constraint Violations

**Symptoms**:
- `null value in column "X" violates not-null constraint`
- `duplicate key value violates unique constraint`
- `insert or update on table "Y" violates foreign key constraint`

**Diagnosis**:
1. Check which specific constraint is failing
2. Trace back to source data or transformation logic
3. Verify that required data is present and valid
4. Check timing of table population (dimensions before facts)

**Solutions**:
1. Make columns nullable if business rules allow
2. Add data validation to catch issues before insertion
3. Ensure proper order of operations (dimensions first)
4. Use appropriate conflict resolution strategies (ON CONFLICT)

### Lookup Table Failures

**Symptoms**:
- Warnings about missing lookup tables
- Missing decoded description columns
- Failed joins during transformation

**Diagnosis**:
1. Check that lookup CSV files exist in `data/raw/lookup/`
2. Verify file naming conventions match expected table names
3. Ensure CSV files have required 'code' and 'description' columns

**Solutions**:
1. Obtain missing HMDA lookup tables from official sources
2. Create placeholder lookup tables if not needed for analysis
3. Modify transform code to gracefully handle missing lookups
4. Update documentation about which lookups are required

### Connection and Environment Issues

**Symptoms**:
- Database connection failures
- Missing environment variables
- Permission errors

**Diagnosis**:
1. Verify `.env` file contains required variables:
   - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
2. Check network connectivity to database server
3. Validate user permissions and schema access rights
4. Confirm PostgreSQL service is running

**Solutions**:
1. Copy `.env.example` to `.env` and fill in values
2. Test connection with `psql` or similar tool
3. Grant appropriate permissions to database user
4. Restart services or contact DBA as needed

## Specific Error Resolutions

### "column "fiec_msa_md_median_family_income" does not exist"

**Cause**: Spelling inconsistency between source (`ffiec`) and code/database (`fiec`)

**Fix**: 
1. Standardize on `ffiec_msa_md_median_family_income` everywhere
2. Update SQL files, Python code, and documentation
3. Verify source column name matches after cleaning

### "profile_hash column missing" or "invalid profile_hash"

**Cause**: 
- Profile hash computation failing
- Mismatch between staging and dimension table expectations

**Fix**:
1. Verify applicant profile columns list is complete
2. Check that column name cleaning is applied before hash computation
3. Ensure hash function handles null/missing values consistently
4. Validate CHAR(64) length matches SHA-256 hex digest length

### "cannot truncate table ... because it is referenced by a foreign key constraint"

**Cause**: Fact table has foreign key dependency on staging table

**Fix**:
1. Remove inappropriate foreign key from fact table to staging table
2. Use source_row_id as a simple reference column without FK constraint
3. Maintain lineage through application logic rather than database constraints
4. If lineage tracking is critical, implement a separate audit table

## Debugging Techniques

### Enable Detailed Logging
1. Change log level to DEBUG in `src/main.py` or `.env`
2. Add specific logger calls in problematic areas
3. Log column names at each processing stage

### Data Sampling for Testing
1. Create a small subset of data for rapid testing:
   ```bash
   head -n 1000 data/raw/state_CA.csv > data/raw/sample.csv
   ```
2. Temporarily modify `src/config.py` to point to sample file
3. Run ETL on sample to verify fixes
4. Scale back to full dataset

### Intermediate Data Inspection
1. Check intermediate Parquet files:
   - `data/processed/hmda_clean.parquet` (final clean data)
   - `data/processed/hmda_rejected.parquet` (rejected records)
2. Use SQL queries to inspect staging and dimension tables
3. Verify row counts match expectations at each stage

## Validation Checks

Run these queries to verify data integrity:

```sql
-- Check for null keys in fact table
SELECT 
    'lei_key_null' AS check_type, COUNT(*) AS count
FROM analytics.fact_loan_application 
WHERE lei_key IS NULL
UNION ALL
SELECT 'geography_key_null', COUNT(*) 
FROM analytics.fact_loan_application 
WHERE geography_key IS NULL
UNION ALL
-- Add similar checks for other foreign keys

-- Verify row counts match
SELECT 
    'staging_rows' AS metric, COUNT(*) AS count FROM staging.hmda_raw
UNION ALL
SELECT 'fact_rows', COUNT(*) FROM analytics.fact_loan_application
UNION ALL
SELECT 'dim_lender', COUNT(*) FROM analytics.dim_lender
UNION ALL
SELECT 'dim_geography', COUNT(*) FROM analytics.dim_geography
-- etc.

-- Check for orphaned records (fact rows without dimension parents)
SELECT 'orphaned_loans' AS issue, COUNT(*) AS count
FROM analytics.fact_loan_application f
LEFT JOIN analytics.dim_loan l ON f.loan_key = l.loan_key
WHERE l.loan_key IS NULL
```

## When to Escalate

Contact the data engineering team if:
1. Schema changes are required in source systems
2. Performance optimization exceeds basic tuning
3. Data quality issues suggest upstream process problems
4. Production data loss or corruption is suspected