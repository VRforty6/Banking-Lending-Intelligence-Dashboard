# Banking Lending Intelligence Dashboard

An end-to-end lending analytics project built on U.S. Home Mortgage Disclosure Act (HMDA) data.

The project transforms more than 1.16 million California mortgage application records into a PostgreSQL analytical warehouse for lending performance, approval and denial analysis, borrower characteristics, geography, lender performance, and portfolio analysis.

## Business Problem

Financial institutions need reliable visibility into:

- Loan application volume and outcomes
- Approval and denial patterns
- Borrower and applicant characteristics
- Geographic lending distribution
- Lender performance
- Loan portfolio composition
- Lending and risk indicators

This project builds the analytical data foundation required to evaluate those areas consistently at scale.

## Current Status

**Backend data warehouse and ETL pipeline: Complete and verified**

**Power BI analytics layer: Next phase**

Verified warehouse reconciliation:

| Metric | Result |
|---|---:|
| HMDA records processed | 1,161,292 |
| PostgreSQL staging rows | 1,161,292 |
| Fact rows | 1,161,292 |
| Distinct fact source rows | 1,161,292 |
| Duplicate source rows | 0 |
| Orphan foreign keys | 0 |
| Automated tests | 8 passed |

## Technology Stack

- **Python** - ETL, transformation, validation, and Parquet processing
- **pandas** - data transformation
- **PyArrow / Parquet** - processed data storage and batch ingestion
- **PostgreSQL 18** - analytical data warehouse
- **SQLAlchemy** - Python/PostgreSQL integration
- **SQL** - dimensional modeling, validation, and analytical queries
- **pytest** - automated validation
- **Power BI** - semantic model and dashboard layer
- **Git / GitHub** - source control and project documentation

## Data Architecture

The pipeline follows:

~~~text
HMDA Source Data
        |
        v
Python Cleaning / Transformation
        |
        v
Parquet
        |
        v
PostgreSQL Staging
        |
        v
Dimensional Warehouse
        |
        v
Power BI
~~~

## Analytical Model

The PostgreSQL warehouse contains:

- `analytics.dim_lender`
- `analytics.dim_geography`
- `analytics.dim_loan`
- `analytics.dim_applicant_profile`
- `analytics.dim_action_taken`
- `analytics.fact_loan_application`

Verified dimension sizes:

| Dimension | Rows |
|---|---:|
| Lender | 1,160 |
| Geography | 9,042 |
| Loan | 320 |
| Applicant Profile | 156,927 |
| Action Taken | 8 |

## ETL Reliability

The production pipeline includes:

- Batched ingestion of the full 1,161,292-row Parquet dataset
- Deterministic surrogate-key resolution
- Seven-field `dim_loan` business grain
- PostgreSQL `UNIQUE NULLS NOT DISTINCT` enforcement
- NULL-safe joins using `IS NOT DISTINCT FROM`
- Deterministic handling of incomplete HMDA geography records
- Idempotent dimension loading
- Atomic full refresh of the fact table
- Environment-based PostgreSQL configuration
- Automated validation tests

## Data Quality and Reconciliation

Before fact loading, the pipeline validates dimension coverage for:

- Lender
- Geography
- Loan
- Applicant profile
- Action taken

Final reconciliation:

~~~text
Staging rows:             1,161,292
Fact rows:                1,161,292
Distinct source rows:     1,161,292
Duplicate source rows:            0
Orphan foreign keys:              0
~~~

## Dataset Storage

The full HMDA datasets are intentionally excluded from Git because of their size.

Ignored local files include:

~~~text
data/raw/*.csv
data/processed/*.parquet
~~~

The ETL code, database schema, validation logic, analytical SQL, tests, and documentation remain version controlled.

## Repository Structure

~~~text
Banking-Lending-Intelligence-Dashboard/
|
|-- data/
|   |-- raw/                 # Local HMDA source files, Git ignored
|   `-- processed/           # Generated Parquet files, Git ignored
|
|-- docs/                    # Architecture, lineage, ETL and validation docs
|-- scripts/                 # Project utilities
|-- sql/                     # Warehouse DDL, loading and analytical queries
|-- src/                     # Data preparation and validation modules
|-- tests/                   # Automated tests
|
|-- etl_hmda.py
|-- load_data.py
|-- smoke_test_etl.py
|-- requirements.txt
|-- .env.example
|-- README.md
`-- STATUS_UPDATE.md
~~~

## SQL Layer

The `sql/` directory contains:

1. Database creation
2. Schema creation
3. Dimensional warehouse DDL
4. Data-loading SQL
5. Analytical views
6. Validation queries
7. Business-analysis queries

## Configuration

Create a local `.env` file based on `.env.example`:

~~~text
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=banking_lending_intelligence
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
~~~

Credentials are intentionally excluded from Git.

## Validation

Run the automated tests with:

~~~powershell
python -m pytest -q
~~~

Current verified result:

~~~text
8 passed
~~~

The remaining pandas `FutureWarning` messages are non-blocking and do not affect warehouse reconciliation.

## Power BI - Next Phase

The verified PostgreSQL warehouse will support:

1. Lending Executive Overview
2. Approval and Denial Analysis
3. Borrower and Applicant Profile Analysis
4. Geographic Lending Intelligence
5. Lender Performance
6. Loan Portfolio and Risk Indicators

The Power BI layer will use the reconciled analytical warehouse rather than querying raw HMDA files directly.

## Documentation

Detailed documentation under `docs/` includes:

- Data lineage
- Database model
- ETL process
- Schema mapping
- SQL validation
- Troubleshooting

## Project Goal

The final project demonstrates an end-to-end analytics workflow:

**raw lending data -> data engineering -> dimensional warehouse -> validation -> business intelligence**
