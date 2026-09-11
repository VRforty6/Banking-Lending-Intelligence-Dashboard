# Database Model

## Schema Overview

The database consists of three schemas:

1. **staging**: Contains the raw data loaded from the Parquet file.
2. **analytics**: Contains the dimensional model (fact and dimension tables) and analytical views.
3. **audit**: (Not used in this phase, but reserved for future audit tables.)

## Staging Table

### staging.hmda_raw

This table preserves all columns from the Parquet file, with the addition of:
- `stg_row_id`: A surrogate key (BIGSERIAL) serving as the primary key.
- `load_timestamp`: Timestamp indicating when the row was loaded.

The columns correspond to the HMDA Loan Application Register (LAR) fields, with the following exceptions:
- `activity_year`, `action_taken`, `loan_amount`, and `income` are typed as `BIGINT`, `BIGINT`, `DOUBLE PRECISION`, and `DOUBLE PRECISION` respectively.
- All other columns are stored as `TEXT`.

## Dimensional Model (Analytics Schema)

### Fact Table

#### fact_loan_application
- **Grain**: One row per HMDA loan application record.
- **Primary Key**: `fact_loan_application_key` (SERIAL)
- **Foreign Keys**:
  - `lei_key` → `dim_lender.lei_key`
  - `geography_key` → `dim_geography.geography_key`
  - `loan_key` → `dim_loan.loan_key`
  - `applicant_profile_key` → `dim_applicant_profile.applicant_profile_key`
  - `action_taken_key` → `dim_action_taken.action_taken_key`
- **Measures**:
  - `loan_amount`: The loan amount applied for.
  - `income`: The applicant's income.
- **Attributes**:
  - `application_year`: The year of the application (from `activity_year`).
  - `load_timestamp`: When the fact row was loaded.
  - `source_row_id`: The `stg_row_id` from the staging table, enabling traceability to the raw data.

### Dimension Tables

#### dim_lender
- **Key**: `lei_key` (SERIAL)
- **Attributes**:
  - `lei`: The Legal Entity Identifier of the lender.

#### dim_geography
- **Key**: `geography_key` (SERIAL)
- **Attributes**:
  - `state_code`, `county_code`, `census_tract`: Geographic identifiers.
  - Demographic and economic attributes from the census tract:
    - `tract_population`
    - `tract_minority_population_percent`
    - `ffiec_msa_md_median_family_income`
    - `tract_to_msa_income_percentage`
    - `tract_owner_occupied_units`
    - `tract_one_to_four_family_homes`
    - `tracet_median_age_of_housing_units`

#### dim_loan
- **Key**: `loan_key` (SERIAL)
- **Attributes**:
  - `loan_type`, `loan_purpose`, `lien_status`: Core loan characteristics.
  - Additional loan attributes:
    - `reverse_mortgage`
    - `open_end_line_of_credit`
    - `business_or_commercial_purpose`
    - `conforming_loan_limit`

#### dim_applicant_profile
- **Key**: `applicant_profile_key` (SERIAL)
- **Attributes**:
  - Applicant demographics: ethnicity (1-5 and observed), race (1-5 and observed), sex (applicant and co-applicant, observed and not), age (applicant and co-applicant), age over 62 flags.
  - Credit scores: applicant and co-applicant credit score types.
  - Note: Income is a measure in the fact table, not a dimension attribute.

#### dim_action_taken
- **Key**: `action_taken_key` (SERIAL)
- **Attributes**:
  - `action_taken`: The HMDA action taken code (1-8).

## Indexes

Indexes have been created on the foreign key columns in the fact table to improve join performance.

## Notes

- The model adheres to the grain of one row per loan application.
- Dimensions are conformed and can be used to slice and measure the facts.
- The staging table retains all original data for auditing and reprocessing.