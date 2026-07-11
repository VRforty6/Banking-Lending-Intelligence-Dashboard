# ETL Guide for HMDA California Dataset

## Overview
This guide describes how to run the ETL pipeline for processing the HMDA California dataset (`state_CA.csv`). The pipeline reads the raw CSV, cleans and transforms the data, validates it against business rules, and outputs cleaned and rejected datasets.

## Pipeline Structure
The pipeline is implemented in the `src/` directory with the following modules:

- `config.py`: Configuration constants and paths.
- `ingest.py`: Functions to read the CSV file in chunks.
- `clean.py`: Functions to standardize column names and convert data types.
- `transform.py`: Functions to decode categorical fields using lookup tables.
- `validate.py`: Functions to validate data and split into valid and rejected records.
- `main.py`: Orchestrates the ETL process.

## Prerequisites
- Python 3.8+
- Required Python packages (see `requirements.txt`):
  - pandas
  - pyarrow (for Parquet output)

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Lookup Tables
The pipeline expects lookup tables for decoding categorical fields to be located in `data/raw/lookup/`. Each lookup table should be a CSV file with two columns: `code` and `description`. Expected lookup tables include (but are not limited to):
- `action_taken.csv`
- `loan_type.csv`
- `loan_purpose.csv`
- `lien_status.csv`
- `ethnicity.csv`
- `race.csv`
- `sex.csv`
- `applicant_credit_score_type.csv`
- `co_applicant_credit_score_type.csv`
- `reverse_mortgage.csv`
- `open_end_line_of_credit.csv`
- `business_or_commercial_purpose.csv`
- `hoepa_status.csv`
- `negative_amortization.csv`
- `interest_only_payment.csv`
- `balloon_payment.csv`
- `other_nonamortizing_features.csv`
- `construction_method.csv`
- `occupancy_type.csv`
- `manufactured_home_secured_property_type.csv`
- `manufactured_home_land_property_interest.csv`

If a lookup table is missing, the pipeline will skip decoding for that field and log a warning, leaving the codes as integers.

## Transformation Rules
### 1. Cleaning (`clean.py`)
- **Column names**: Converted to lowercase, spaces and hyphens replaced with underscores.
- **Data types**:
  - Columns identified as numeric (by name patterns like `_amount`, `_value`, `_ratio`, `_rate`, `_income`, `_score`, `_age`, etc.) are converted to float, with `'NA'` strings converted to NaN.
  - Columns identified as categorical (by name patterns like `_sex`, `_ethnicity`, `_race`, `_type`, `_status`, `_flag`, `_indicator`, `_code`, or specific prefixes like `aus-`, `denial_reason-`) are converted to nullable integer (`Int64`), with `'NA'` strings converted to NaN.
  - All other columns are treated as strings: whitespace stripped, `'NA'` strings converted to NaN.

### 2. Transformation (`transform.py`)
- For each known categorical column, the pipeline attempts to load a lookup table from `data/raw/lookup/<table_name>.csv`.
- The lookup table is merged with the data on the code column, and a new column `<column_name>_description` is added with the corresponding description.
- If a lookup table is missing, a warning is logged and no description column is added.

### 3. Validation (`validate.py`)
The following validation rules are applied:
- **Required fields**: `activity_year`, `lei`, `census_tract`, `loan_amount`, `action_taken` must not be null.
- **activity_year**: Must be in the set of valid years (default: `{2025}`).
- **lei**: Must be a 20-character alphanumeric string (ISO 20274).
- **state_code**: Must be two uppercase letters.
- **county_code**: Must be exactly 5 digits.
- **census_tract**: Must be exactly 11 digits.
- **loan_amount**: Must be positive when present.
- **income**: Must be non-negative when present.
- **applicant_age** / `co_applicant_age`: Must be between 0 and 110 inclusive when present.
- **loan_to_value_ratio**: Must be between 0 and 500 when present.
- **debt_to_income_ratio**: Must be between 0 and 1000 when present.
- **interest_rate**: Must be between 0 and 30 when present.
- **rate_spread**: Must be between -10 and 30 when present.
- **action_taken**: Must be in the range 1–8.
- **loan_type**: Must be 1, 2, 3, or 4.
- **loan_purpose**: Must be 1, 2, or 3.
- **lien_status**: Must be 1, 2, or 3.
- **hoepa_status**: Must be 1, 2, or 3.
- **Duplicates**: Rows are considered duplicates if they have the same values for the subset [`activity_year`, `lei`, `census_tract`, `loan_amount`, `action_taken`]. Only the first occurrence is kept as valid.

Rows that fail any validation are moved to the rejected dataset with a `rejection_reason` column listing the failed rules.

## Output
The pipeline writes the following files to `data/processed/`:
- `cleaned_data.parquet`: Validated and cleaned data.
- `rejected_data.parquet`: Records that failed validation, with a `rejection_reason` column.
- `validation_report.txt`: A summary report of the ETL run (counts, etc.).

## How to Run
From the project root directory, execute:
```bash
python src/main.py
```

The script will log progress to the console and to `logs/etl.log` (created automatically).

## Monitoring
- Check the console output for progress and any warnings.
- Review the log file for detailed information.
- Examine the validation report for counts of valid and rejected records.

## Troubleshooting
- **Missing lookup tables**: If you see warnings about missing lookup tables, ensure the required CSV files are present in `data/raw/lookup/`.
- **Memory issues**: The pipeline uses chunked reading (default chunk size: 100,000 rows) to minimize memory footprint.
- **Performance**: The pipeline is designed to be repeatable and idempotent; running it again will overwrite the output files.

## Notes
- The original raw file (`data/raw/state_CA.csv`) is never modified.
- The pipeline is designed to handle the HMDA 2025 Loan Application Register (LAR) format.
- For multi-year processing, simply place additional yearly CSVs in `data/raw/` and adjust the `INPUT_FILE_PATH` in `config.py` or modify `main.py` to process multiple files.

## Example Output
After a successful run, you might see output similar to:

```
[INFO] Starting HMDA ETL pipeline.
[INFO] Reading CSV file data/raw/state_CA.csv in chunks of 100000 rows.
[INFO] Finished reading all chunks.
[INFO] Starting data cleaning process.
[INFO] Standardized column names. New columns: [...]
[INFO] Data cleaning completed.
[INFO] Starting decoding of categorical fields using lookup tables.
[INFO] Loaded lookup table 'action_taken' with 8 entries.
[INFO] Applied lookup 'action_taken' to column 'action_taken', created 'action_taken_description'.
...
[INFO] Starting validation of DataFrame.
[INFO] Validation complete. Total: 1161292, Valid: 1000000, Rejected: 161292
[INFO] Writing 1000000 valid records to data/processed/cleaned_data.parquet
[INFO] Writing 161292 rejected records to data/processed/rejected_data.parquet
[INFO] ETL pipeline completed. Report written to data/processed/validation_report.txt
```

## Customization
- To change the chunk size, modify `config.CHUNK_SIZE`.
- To adjust validation rules, edit the functions in `validate.py`.
- To add new lookup tables, simply place the CSV file in `data/raw/lookup/`; the pipeline will automatically attempt to use it if the column name matches.

---
*This guide is based on the pipeline implementation as of the current version.*