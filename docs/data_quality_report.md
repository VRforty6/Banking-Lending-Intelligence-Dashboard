# Data Quality Report

## File Profiled
- state_CA.csv (data/raw/)

## Overview
- Records: 1,161,292 (excluding header)
- Columns: 99
- File format: CSV with header

## Completeness
- Many fields contain the string 'NA' indicating missing or not applicable.
- High missingness observed in: loan_to_value_ratio, interest_rate, rate_spread, total_loan_costs, total_points_and_fees, origination_charges, discount_points, lender_credits, prepayment_penalty_term, intro_rate_period, negative_amortization, interest_only_payment, balloon_payment, other_nonamortizing_features.
- Fields with low missingness: activity_year, lei, state_code, county_code, census_tract, loan_amount, income, applicant_age, co-applicant_age, action_taken, loan_type, loan_purpose, lien_status, etc. (based on sample).

## Validity
- Numeric fields contain valid numeric values where not 'NA'.
- Categorical fields contain codes within expected ranges (based on HMDA specification).
- Date-related field `activity_year` consistently equals 2025 across all rows.

## Uniqueness
- No exact duplicate rows were detected (all rows unique).
- No explicit primary key column; uniqueness would require a composite key (e.g., activity_year, lei, census_tract, loan_amount, action_taken) but not guaranteed.

## Consistency
- Codes appear to follow HMDA coding schemes (requires validation against official lookup tables).
- Geographic identifiers (state_code, county_code, census_tract) are consistent with FIPS standards where applicable.

## Summary
The dataset is suitable for analysis after handling missing values and applying appropriate lookup tables for coded fields. No major data quality issues observed beyond expected missing values in certain financial fields.