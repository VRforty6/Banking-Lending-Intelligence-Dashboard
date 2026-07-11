# Data Profile

## File(s) Profiled
- state_CA.csv (located in data/raw/)

## File Format
- CSV (comma-separated values) with header row.

## Row Count
- 1,161,292 records (excluding header)

## Column Count
- 99 columns

## Grain
- Each row represents a single loan application record (Home Mortgage Disclosure Act Loan Application Register).

## Primary Key Candidate
- No explicit unique identifier column present. A candidate composite key could be (`activity_year`, `lei`, `census_tract`, `loan_amount`, `action_taken`) but uniqueness is not guaranteed. Recommend adding a surrogate key during ETL.

## Reporting Year
- All records have `activity_year = 2025`.

## Data Types Overview
- **Numeric (decimal)**: loan_amount, loan_to_value_ratio, interest_rate, rate_spread, total_loan_costs, total_points_and_fees, origination_charges, discount_points, lender_credits, loan_term, prepayment_penalty_term, intro_rate_period, property_value, total_units, multifamily_affordable_units, income, debt_to_income_ratio, applicant_age, co-applicant_age, tract_population, tract_minority_population_percent, ffiec_msa_md_median_family_income, tract_to_msa_income_percentage, tract_owner_occupied_units, tract_one_to_four_family_homes, tract_median_age_of_housing_units.
- **Integer codes (categorical)**: derived_ethnicity, derived_race, derived_sex, action_taken, purchaser_type, preapproval, loan_type, loan_purpose, lien_status, reverse_mortgage, open-end_line_of_credit, business_or_commercial_purpose, hoepa_status, negative_amortization, interest_only_payment, balloon_payment, other_nonamortizing_features, construction_method, occupancy_type, manufactured_home_secured_property_type, manufactured_home_land_property_interest, applicant_credit_score_type, co-applicant_credit_score_type, applicant_ethnicity-1 through -5, co-applicant_ethnicity-1 through -5, applicant_ethnicity_observed, co-applicant_ethnicity_observed, applicant_race-1 through -5, co-applicant_race-1 through -5, applicant_race_observed, co-applicant_race_observed, applicant_sex, co-applicant_sex, applicant_sex_observed, co-applicant_sex_observed, applicant_age_above_62, co-applicant_age_above_62, submission_of_application, initially_payable_to_institution, aus-1 through aus-5, denial_reason-1 through denial_reason-4.
- **String/Text**: lei, derived_msa-md, state_code, county_code, census_tract, conforming_loan_limit, derived_loan_product_type, derived_dwelling_category (these are actually coded values stored as strings).

## Null / Missing Values
- Many fields contain the string 'NA' representing missing or not applicable. Notable high‑missing fields include: loan_to_value_ratio, interest_rate, rate_spread, total_loan_costs, total_points_and_fees, origination_charges, discount_points, lender_credits, prepayment_penalty_term, intro_rate_period, negative_amortization, interest_only_payment, balloon_payment, other_nonamortizing_features, etc. Exact missing percentages are provided in the Data Quality Report.

## Duplicate Records
- Exact duplicate rows (all columns identical) were not detected; each loan application appears unique.

## Coded Fields Requiring Lookup Tables
- All integer‑coded fields listed above require mapping to their respective meanings (e.g., derived_ethnicity: 1 = Hispanic or Latino, 2 = Not Hispanic or Latino, 3 = Information not provided, etc.). String‑coded fields (lei, census_tract, etc.) may also need external reference tables for geographic or industry definitions.

## Important Dimensions
- **Demographics**: derived_ethnicity, derived_race, derived_sex, applicant_age, co-applicant_age, income, applicant_credit_score_type, co-applicant_credit_score_type.
- **Geography**: state_code, county_code, census_tract, derived_msa-md.
- **Loan Characteristics**: loan_type, loan_purpose, lien_status, loan_amount, loan_to_value_ratio, interest_rate, rate_spread, hoepa_status, etc.
- **Action**: action_taken, purchaser_type, preapproval.

## Important Measures
- loan_amount, income, loan_to_value_ratio, debt_to_income_ratio, interest_rate, rate_spread, total_loan_costs, total_points_and_fees, origination_charges, discount_points, lender_credits, loan_term.