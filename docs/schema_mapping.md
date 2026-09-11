# HMDA Data Schema Mapping

This document maps HMDA data fields from source to final warehouse representation.

## Source CSV Column Names (Raw)
As found in `state_CA.csv` header:

```
activity_year,lei,derived_msa-md,state_code,county_code,census_tract,conforming_loan_limit,derived_loan_product_type,derived_dwelling_category,derived_ethnicity,derived_race,derived_sex,action_taken,purchaser_type,preapproval,loan_type,loan_purpose,lien_status,reverse_mortgage,open-end_line_of_credit,business_or_commercial_purpose,loan_amount,loan_to_value_ratio,interest_rate,rate_spread,hoepa_status,total_loan_costs,total_points_and_fees,origination_charges,discount_points,lender_credits,loan_term,prepayment_penalty_term,intro_rate_period,negative_amortization,interest_only_payment,balloon_payment,other_nonamortizing_features,property_value,construction_method,occupancy_type,manufactured_home_secured_property_type,manufactured_land_property_interest,total_units,multifamily_affordable_units,income,debt_to_income_ratio,applicant_credit_score_type,co-applicant_credit_score_type,applicant_ethnicity-1,applicant_ethnicity-2,applicant_ethnicity-3,applicant_ethnicity-4,applicant_ethnicity-5,co-applicant_ethnicity-1,co-applicant_ethnicity-2,co-applicant_ethnicity-3,co-applicant_ethnicity-4,co-applicant_ethnicity-5,applicant_ethnicity_observed,co-applicant_ethnicity_observed,applicant_race-1,applicant_race-2,applicant_race-3,applicant_race-4,applicant_race-5,co-applicant_race-1,co-applicant_race-2,co-applicant_race-3,co-applicant_race-4,co-applicant_race-5,applicant_race_observed,co-applicant_race_observed,applicant_sex,co-applicant_sex,applicant_sex_observed,co-applicant_sex_observed,applicant_age,co-applicant_age,applicant_age_above_62,co-applicant_age_above_62,submission_of_application,initially_payable_to_institution,aus-1,aus-2,aus-3,aus-4,aus-5,denial_reason-1,denial_reason-2,denial_reason-3,denial_reason-4,tract_population,tract_minority_population_percent,ffiec_msa_md_median_family_income,tract_to_msa_income_percentage,tract_owner_occupied_units,tract_one_to_four_family_homes,tract_median_age_of_housing_units
```

## Canonical Schema (Snake_case)
After applying `_clean_column_names()` function (lowercase, hyphen/space to underscore, deduplicate underscores, strip):

```
activity_year,lei,derived_msa_md,state_code,county_code,census_tract,conforming_loan_limit,derived_loan_product_type,derived_dwelling_category,derived_ethnicity,derived_race,derived_sex,action_taken,purchaser_type,preapproval,loan_type,loan_purpose,lien_status,reverse_mortgage,open_end_line_of_credit,business_or_commercial_purpose,loan_amount,loan_to_value_ratio,interest_rate,rate_spread,hoepa_status,total_loan_costs,total_points_and_fees,origination_charges,discount_points,lender_credits,loan_term,prepayment_penalty_term,intro_rate_period,negative_amortization,interest_only_payment,balloon_payment,other_nonamortizing_features,property_value,construction_method,occupancy_type,manufactured_home_secured_property_type,manufactured_home_land_property_interest,total_units,multifamily_affordable_units,income,debt_to_income_ratio,applicant_credit_score_type,co_applicant_credit_score_type,applicant_ethnicity_1,applicant_ethnicity_2,applicant_ethnicity_3,applicant_ethnicity_4,applicant_ethnicity_5,co_applicant_ethnicity_1,co_applicant_ethnicity_2,co_applicant_ethnicity_3,co_applicant_ethnicity_4,co_applicant_ethnicity_5,applicant_ethnicity_observed,co_applicant_ethnicity_observed,applicant_race_1,applicant_race_2,applicant_race_3,applicant_race_4,applicant_race_5,co_applicant_race_1,co_applicant_race_2,co_applicant_race_3,co_applicant_race_4,co_applicant_race_5,applicant_race_observed,co_applicant_race_observed,applicant_sex,co_applicant_sex,applicant_sex_observed,co_applicant_sex_observed,applicant_age,co_applicant_age,applicant_age_above_62,co_applicant_above_62,submission_of_application,initially_payable_to_institution,aus_1,aus_2,aus_3,aus_4,aus_5,denial_reason_1,denial_reason_2,denial_reason_3,denial_reason_4,tract_population,tract_minority_population_percent,ffiec_msa_md_median_family_income,tract_to_msa_income_percentage,tract_owner_occupied_units,tract_one_to_four_family_homes,tract_median_age_of_housing_units
```

## Staging Table Schema (`staging.hmda_raw`)
From `sql/03_create_tables.sql`:
- Keeps all canonical column names from cleaned CSV
- Adds `stg_row_id` (BIGSERIAL PRIMARY KEY)
- Adds `load_timestamp` (TIMESTAMP WITH TIME ZONE)
- Specific type conversions:
  - `activity_year`: BIGINT
  - `action_taken`: BIGINT
  - `loan_amount`: DOUBLE PRECISION
  - `income`: DOUBLE PRECISION
  - All other columns: TEXT

## Dimension and Fact Table Schemas
### dim_lender
- lei_key (SERIAL PK)
- lei (TEXT)

### dim_geography
- geography_key (SERIAL PK)
- state_code, county_code, census_tract (TEXT)
- tract_population (BIGINT)
- tract_minority_population_percent (DOUBLE PRECISION)
- ffiec_msa_md_median_family_income (DOUBLE PRECISION)
- tract_to_msa_income_percentage (DOUBLE PRECISION)
- tract_owner_occupied_units (BIGINT)
- tract_one_to_four_family_homes (BIGINT)
- tract_median_age_of_housing_units (INTEGER)

### dim_loan
- loan_key (SERIAL PK)
- loan_type, loan_purpose, lien_status (TEXT)
- reverse_mortgage, open_end_line_of_credit, business_or_commercial_purpose, conforming_loan_limit (TEXT)

### dim_applicant_profile
- applicant_profile_key (SERIAL PK)
- All applicant demographics and credit score fields (TEXT)
- profile_hash (CHAR(64) UNIQUE) - for deduplication

### dim_action_taken
- action_taken_key (SERIAL PK)
- action_taken (INTEGER)

### fact_loan_application
- fact_loan_application_key (SERIAL PK)
- lei_key (FK to dim_lender)
- geography_key (FK to dim_geography)
- loan_key (FK to dim_loan)
- applicant_profile_key (FK to dim_applicant_profile)
- action_taken_key (FK to dim_action_taken)
- loan_amount (DOUBLE PRECISION)
- income (DOUBLE PRECISION)
- application_year (INTEGER) - from activity_year
- load_timestamp (TIMESTAMP WITH TIME ZONE)
- source_row_id (BIGINT) - references staging.hmda_raw.stg_row_id

## Analytics Views
See `sql/05_create_views.sql` for analytical views that aggregate and present the data.

## Column Name Mapping Summary
Source (CSV) → Canonical (cleaned) → Staging/Warehouse
- derived_msa-md → derived_msa_md → derived_msa_md
- applicant_ethnicity-1 → applicant_ethnicity_1 → applicant_ethnicity_1
- co-applicant_credit_score_type → co_applicant_credit_score_type → co_applicant_credit_score_type
- open-end_line_of_credit → open_end_line_of_credit → open_end_line_of_credit
- aus-1 → aus_1 → aus_1
- denial_reason-1 → denial_reason_1 → denial_reason_1
- ffiec_msa_md_median_family_income → ffiec_msa_md_median_family_income → ffiec_msa_md_median_family_incom

Note: The spelling "ffiec" is correct in the source and should be maintained throughout.