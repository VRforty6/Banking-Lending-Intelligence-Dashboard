# Project Status

## Current Phase

Backend data warehouse and ETL pipeline complete and verified. Power BI dashboard development is the next phase.

## Verified Dataset

- HMDA California records: 1,161,292
- PostgreSQL staging rows: 1,161,292
- Fact loan application rows: 1,161,292
- Distinct fact source row IDs: 1,161,292
- Duplicate source row IDs: 0
- Orphan foreign keys: 0

## Warehouse

PostgreSQL analytics model includes:

- `analytics.dim_lender`
- `analytics.dim_geography`
- `analytics.dim_loan`
- `analytics.dim_applicant_profile`
- `analytics.dim_action_taken`
- `analytics.fact_loan_application`

Verified dimension counts:

- Lenders: 1,160
- Geography members: 9,042
- Loan dimension members: 320
- Applicant profiles: 156,927
- Action outcomes: 8

## ETL Reliability

The current pipeline includes:

- Full Parquet batch ingestion across all 1,161,292 rows
- Seven-field `dim_loan` business grain
- NULL-safe loan-dimension matching using `IS NOT DISTINCT FROM`
- `UNIQUE NULLS NOT DISTINCT` enforcement for the loan business key
- Deterministic handling of incomplete HMDA geography records
- Atomic full refresh of the fact table
- Idempotent dimension loading
- PostgreSQL connection configuration through `.env`

## Validation

Automated test suite:

- 8 tests passed
- 0 failures
- 17 non-blocking pandas FutureWarnings

Warehouse reconciliation also confirmed zero unmatched dimension references before fact loading.

## Repository

Raw and processed HMDA datasets are intentionally excluded from Git:

- `data/raw/*.csv`
- `data/processed/*.parquet`

The local source and generated datasets remain available for pipeline execution but are not stored in the public repository.

## Next Phase

Build the Power BI semantic model and dashboard using the verified PostgreSQL warehouse.

Planned analytical areas:

1. Lending Executive Overview
2. Approval and Denial Analysis
3. Borrower and Applicant Profile Analysis
4. Geographic Lending Intelligence
5. Lender Performance
6. Loan Portfolio and Risk Indicators
