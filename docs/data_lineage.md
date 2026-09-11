# Data Lineage

## Overview

This document describes the flow of data from the raw HMDA Parquet file through the ETL process into the analytical star schema in PostgreSQL.

## Data Sources

- **Source**: HMDA Loan Application Register (LAR) data in Apache Parquet format.
- **Location**: `data/processed/hmda_clean.parquet`
- **Row Count**: 1,161,292 (as validated)

## ETL Process

The ETL process is implemented in the Python script `load_data.py` (see below) and consists of the following stages:

### 1. Staging Load
- **Source**: Parquet file (`data/processed/hmda_clean.parquet`)
- **Target**: `staging.hmda_raw` table in the `staging` schema.
- **Method**:
  - The Parquet file is read using `pandas.read_parquet()` (or `pyarrow.parquet`).
  - A DataFrame is created with all columns from the Parquet file.
  - Two additional columns are added:
    - `stg_row_id`: A sequence-generated unique identifier for each row.
    - `load_timestamp`: Set to the current timestamp at the time of load.
  - The DataFrame is inserted into the `staging.hmda_raw` table using `to_sql()` with `if_exists='replace'` (or `append` if incremental loading is required in the future).

### 2. Transformation to Star Schema
- **Source**: `staging.hmda_raw`
- **Target**: Dimension and fact tables in the `analytics` schema.
- **Method**:
  - The transformation is performed using SQL `INSERT INTO ... SELECT` statements.
  - Dimension tables are loaded with distinct values from the staging table, ensuring referential integrity.
  - The fact table is populated by joining the staging table with the dimension tables to retrieve surrogate keys.
  - The following transformations occur:
    - **`staging.hmda_raw` → `analytics.dim_lender`**:
      - Extract distinct `lei` values.
      - Generate `lei_key` as surrogate.
    - **`staging.hmda_raw` → `analytics.dim_geography`**:
      - Extract distinct combinations of `state_code`, `county_code`, `census_tract`.
      - Include associated demographic and economic attributes.
      - Generate `geography_key` as surrogate.
    - **`staging.hmda_raw` → `analytics.dim_loan`**:
      - Extract distinct combinations of `loan_type`, `loan_purpose`, `lien_status`, `reverse_mortgage`, `open_end_line_of_credit`, `business_or_commercial_purpose`, `conforming_loan_limit`.
      - Generate `loan_key` as surrogate.
    - **`staging.hmda_raw` → `analytics.dim_applicant_profile`**:
      - Extract distinct combinations of all applicant demographic and credit score attributes.
      - Generate `applicant_profile_key` as surrogate.
    - **`staging.hmda_raw` → `analytics.dim_action_taken`**:
      - Extract distinct `action_taken` values.
      - Generate `action_taken_key` as surrogate.
    - **`staging.hmda_raw` + dimension lookups → `analytics.fact_loan_application`**:
      - For each row in `staging.hmda_raw`:
        - Look up `lei_key` from `dim_lender` using `lei`.
        - Look up `geography_key` from `dim_geography` using (`state_code`, `county_code`, `census_tract`).
        - Look up `loan_key` from `dim_loan` using (`loan_type`, `loan_purpose`, `lien_status`, `reverse_mortgage`, `open_end_line_of_credit`, `business_or_commercial_purpose`, `conforming_loan_limit`).
        - Look up `applicant_profile_key` from `dim_applicant_profile` using all applicant demographic and credit score columns.
        - Look up `action_taken_key` from `dim_action_taken` using `action_taken`.
        - Copy `loan_amount` and `income` as measures.
        - Copy `activity_year` as `application_year`.
        - Set `source_row_id` to the `stg_row_id` from the staging table.
        - Set `load_timestamp` to the current timestamp.
  - The insertions are done in a transaction to ensure consistency.

### 3. Indexing
- After loading the fact table, indexes are created on the foreign key columns to optimize query performance.

### 4. View Creation
- Analytical views are created in the `analytics` schema to provide ready-to-use aggregates and insights.

## Data Quality and Validation

- The staging table preserves all original data, including nulls and invalid values, for auditing.
- The transformation process includes implicit data validation:
  - Only valid `lei` values that exist in the staging table are used to populate the dimension.
  - Referential integrity is enforced via foreign key constraints in the fact table.
- Validation queries (see `sql_validation.md`) are run to ensure:
  - Row counts match between source, staging, and fact.
  - No orphaned records in the fact table.
  - No invalid values in key fields.

## Output

The end result is a star schema in the `analytics` schema consisting of:
- One fact table: `fact_loan_application`
- Five dimension tables: `dim_lender`, `dim_geography`, `dim_loan`, `dim_applicant_profile`, `dim_action_taken`
- A set of analytical views for reporting and visualization.

This model is optimized for query performance and supports the analytical requirements for Power BI reporting.