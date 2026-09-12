# Banking Lending Intelligence Dashboard: Project Walkthrough

## 1. Business objective

The Banking Lending Intelligence project turns public mortgage application data into an analytics-ready warehouse and Power BI reporting layer for lending performance, approval and denial trends, geography, borrower profiles, and data quality.

The business goal is to help a banking, lending, compliance, or analytics team answer questions such as:

- How many mortgage applications were received, originated, denied, withdrawn, or approved but not accepted?
- How do outcomes vary by state, county, loan purpose, lender, applicant profile, and income band?
- Are application volumes and lending outcomes reconciled from raw source files through the analytical fact table?
- Can leadership trust the dashboard totals and drilldowns?

The project was designed as a full data engineering and business intelligence workflow, not just a dashboard. It includes raw data ingestion, validation, rejected-row handling, a consolidated Parquet layer, PostgreSQL staging, dimensional modeling, warehouse validation, analytical views, and a Power BI PBIP semantic model with report pages.

## 2. Why HMDA was selected

HMDA, the Home Mortgage Disclosure Act dataset, was selected because it is public, large, real-world, and analytically rich.

It is a strong fit for a portfolio project because it has the same challenges that appear in production data work:

- Large row counts that require chunked processing and efficient loading.
- Many coded categorical fields that need business-readable labels.
- Geographic and applicant demographic dimensions.
- Fact-like application records with measurable outcomes.
- Data quality edge cases such as missing counties, null fields, invalid action codes, and schema consistency risks.
- Clear business use cases for lending operations, compliance analytics, and executive reporting.

The current verified warehouse uses HMDA public mortgage data for five states: CA, TX, FL, NY, and IL. The currently loaded years are 2023, 2024, and 2025, covering 15 logical year/state combinations.

## 3. End-to-end architecture

The project architecture flows from raw HMDA CSV files into a validated analytical model:

1. Raw HMDA CSV files land in `data/raw`.
2. Python discovers files using the production naming convention.
3. Pandas processes each CSV sequentially in chunks.
4. Cleaning and validation logic separates valid rows from rejected rows.
5. Valid rows are consolidated into `data/processed/hmda_clean.parquet`.
6. Rejected rows are consolidated into `data/processed/hmda_rejected.parquet`.
7. PostgreSQL staging loads the clean Parquet data into `staging.hmda_raw`.
8. Dimension tables are populated from staging.
9. `analytics.fact_loan_application` is populated by joining staging to dimensions.
10. Validation queries reconcile staging, fact, duplicate source rows, mandatory keys, and unmatched dimension keys.
11. SQL views expose common analytical summaries.
12. Power BI connects through a PBIP semantic model and report pages.

The main technologies in the repository are PostgreSQL 18, Python, pandas, pyarrow, SQLAlchemy, psycopg2, and Power BI PBIP.

## 4. Raw file naming and ingestion strategy

The original implementation was California-only and assumed a single raw file. That made the pipeline simple, but it also made the design brittle. The project was refactored to support deterministic raw-file naming conventions for both per-state and yearly multi-state files:

```text
hmda_<YEAR>_<STATE>.csv
hmda_<YEAR>_multi_state.csv
```

Examples:

```text
hmda_2023_multi_state.csv
hmda_2024_CA.csv
hmda_2024_TX.csv
hmda_2025_FL.csv
```

The ingestion layer discovers matching files in `data/raw` instead of hard-coding `state_CA.csv`. The supported scope evolved from one California file to multiple states and years. The current verified state is five states and three years:

- CA
- TX
- FL
- NY
- IL
- 2023
- 2024
- 2025

The 2023 source is one yearly multi-state CSV, `hmda_2023_multi_state.csv`. The 2024 and 2025 sources use per-state files. Together, they cover 15 logical year/state combinations. The pipeline validates that each row's `activity_year` matches the filename year. For per-state files, `state_code` must match the filename state. For multi-state files, `state_code` must be one of the supported states, and all five expected states must be present. Ambiguous same-year coverage fails clearly so rows are not double-counted.

## 5. Chunked Python ETL

The ETL layer uses pandas chunking so the pipeline can process large HMDA CSV files without loading every source row into memory at once.

The important design choices are:

- Source files are processed sequentially.
- CSV chunks are processed sequentially.
- Cleaning and validation behavior is applied consistently across all files.
- Reconciliation counters are updated as the pipeline goes.
- The output schema remains compatible across chunks and files.

This approach keeps memory usage bounded while still producing one consolidated analytical dataset.

## 6. Validation and rejected-row handling

The ETL validates required fields and known domain constraints before data reaches the warehouse.

Rejected rows are not discarded silently. They are written to:

```text
data/processed/hmda_rejected.parquet
```

Each rejected row includes rejection context so failures can be audited. The pipeline also produces reconciliation counts:

- Total input rows.
- Valid rows.
- Rejected rows.
- Reconciliation difference.
- Counts by source file.
- Counts by year.
- Counts by state.

For the current 2023–2025 five-state dataset, all 12,006,526 source rows passed ETL validation, with 0 rejected rows and a reconciliation difference of 0.

## 7. Consolidated Parquet layer

All valid rows from the discovered source files are appended into:

```text
data/processed/hmda_clean.parquet
```

This Parquet layer is the handoff between Python ETL and PostgreSQL loading. It gives the project a stable, columnar, analytics-friendly intermediate layer.

The production HMDA schema currently uses 99 columns. Keeping a consolidated Parquet file makes it easier to:

- Re-run the warehouse load without re-reading every raw CSV.
- Validate row counts before loading PostgreSQL.
- Preserve source-level fields for staging.
- Avoid schema drift between chunks and files.

## 8. PostgreSQL staging architecture

PostgreSQL staging uses `staging.hmda_raw` as the warehouse landing table for valid HMDA records.

The staging table keeps source-grain rows and includes generated operational fields:

- `stg_row_id`
- `load_timestamp`
- `profile_hash`

The current verified staging table contains 12,006,526 rows.

Staging is intentionally separate from the analytics schema. This lets the warehouse preserve a raw-ish relational landing layer while still building clean star-schema dimensions and facts downstream.

## 9. PostgreSQL COPY FROM STDIN optimization

The original staging loader used pandas and SQLAlchemy multi-row insert behavior. That approach was too slow for multi-million-row HMDA loading. A benchmark before optimization was roughly 18 minutes for 100,000 rows, which made a full multi-state load impractical.

The staging load path was optimized to use PostgreSQL native `COPY FROM STDIN` through the existing SQLAlchemy and psycopg2 connection.

The optimized loader:

- Preserves `get_parquet_batches()`.
- Preserves `stg_row_id`, `load_timestamp`, and `profile_hash` generation.
- Uses explicit staging column order.
- Uses an in-memory `StringIO` CSV buffer per batch.
- Handles nulls deterministically.
- Avoids multi-GB temporary CSV files.
- Keeps batch logging and cumulative row counts.

The measured COPY benchmark loaded 100,000 rows in 9.788 seconds, about 10,216 rows per second. That changed the warehouse load from a bottleneck into a practical workflow.

## 10. Star-schema design

The analytics layer uses a star schema centered on:

```text
analytics.fact_loan_application
```

The fact table joins to five dimensions:

- `analytics.dim_lender`
- `analytics.dim_geography`
- `analytics.dim_loan`
- `analytics.dim_applicant_profile`
- `analytics.dim_action_taken`

This structure gives Power BI a clean analytical model with dimensions filtering a single fact table. The design supports executive KPIs, lending outcome diagnostics, geography drilldowns, lender analysis, and applicant profile segmentation.

## 11. dim_lender

`dim_lender` stores lender identity at the LEI grain.

The project avoids inventing lender names when the source does not provide an enriched lender-name field. Where only LEI is available, the model keeps LEI rather than creating unsupported labels.

Business role:

- Enables application volume and outcome analysis by lender.
- Provides the lender key used by the fact table.

## 12. dim_geography

`dim_geography` stores geography attributes such as state, county, census tract, and tract-level demographic fields.

The geography dimension had one of the most important edge cases in the project. A Texas row had:

```text
state_code = TX
county_code = NULL
census_tract = 48113007206
```

The fact logic derived county `48113` using `LEFT(census_tract, 5)`, but the dimension population originally excluded rows where `county_code IS NULL`. That created an inconsistency between dimension normalization and fact joins.

The fix was to canonicalize geography consistently:

```sql
CASE
    WHEN county_code IS NOT NULL THEN county_code
    WHEN census_tract IS NOT NULL THEN LEFT(census_tract, 5)
    ELSE 'UNKNOWN'
END AS county_code
```

Rows with a census tract are now allowed into `dim_geography` even if `county_code` is missing.

## 13. dim_loan

`dim_loan` represents loan characteristics. It was corrected to a seven-field business grain:

- `loan_type`
- `loan_purpose`
- `lien_status`
- `reverse_mortgage`
- `open_end_line_of_credit`
- `business_or_commercial_purpose`
- `conforming_loan_limit`

This correction was important because an incomplete loan grain can collapse distinct loan products into the same dimension record. The seven-field grain better preserves business meaning while keeping the model manageable.

## 14. dim_applicant_profile

`dim_applicant_profile` stores applicant profile attributes such as ethnicity, race, sex, age, age-over-62 flags, and credit score type fields.

The dimension uses a `profile_hash` generated from selected applicant-profile fields. This gives the fact table a stable way to join applicant profile combinations without building a very wide fact table.

Business role:

- Supports segmentation of outcomes by applicant characteristics.
- Keeps applicant profile attributes out of the central fact table.
- Provides reusable demographic slicing in Power BI.

## 15. dim_action_taken

`dim_action_taken` stores HMDA action taken codes.

These codes drive the core lending outcome measures:

- Originated applications.
- Denied applications.
- Withdrawn applications.
- Approved but not accepted applications.
- Incomplete applications.

The Power BI semantic model adds business-readable labels so dashboard users do not have to interpret raw HMDA numeric codes.

## 16. fact_loan_application

`fact_loan_application` is the central analytical fact table. It stores one row per valid HMDA source record loaded from staging.

The current verified fact table contains 12,006,526 rows.

Key fact fields include:

- Lender key.
- Geography key.
- Loan key.
- Applicant profile key.
- Action taken key.
- Loan amount.
- Income.
- Application year.
- Source row id.
- Load timestamp.

The fact table is designed for aggregate reporting in Power BI and SQL views.

## 17. Dimension business keys and joins

The warehouse uses business keys from staging to populate dimensions and then joins staging rows back to those dimensions to populate the fact table.

Important join patterns include:

- Lender joins by LEI.
- Geography joins by normalized state, county, and tract.
- Loan joins by the seven-field loan grain.
- Applicant profile joins by `profile_hash`.
- Action taken joins by action code.

The project validates that the fact table does not contain unmatched dimension keys. The current warehouse has zero unmatched dimension keys.

## 18. Dynamic warehouse validation

Validation originally hard-coded the California-only expected row count of 1,161,292. That worked for the first state, but it became incorrect as the warehouse grew to multiple states and years.

The validation logic was redesigned to be dynamic. Instead of comparing to a fixed California row count, it now separates validation into two layers.

Python ETL validation reconciles raw input to valid and rejected Parquet output. PostgreSQL warehouse validation reconciles staging to fact and checks duplicates, mandatory keys, invalid values, and unmatched dimension keys.

The duplicate-source-row validation was also corrected. The old query could return `NULL` when no duplicates existed. It now returns integer `0`, which makes the validation result explicit and reliable.

Current verified integrity checks:

- 12,006,526 staging rows.
- 12,006,526 fact rows.
- Zero duplicate source rows.
- Zero null mandatory fact keys.
- Zero invalid action codes.
- Zero invalid non-positive loan amounts.
- Zero unmatched dimension keys.
- Zero staging-to-fact reconciliation difference.

## 19. Analytics views

The SQL layer includes analytical views for common reporting needs, including:

- Lending overview.
- Application outcomes.
- Borrower analysis.
- Geographic analysis.
- Lender performance.
- Data quality.

One compatibility issue came from using `MEDIAN()`, which is not a PostgreSQL built-in aggregate in this environment. The fix was to use PostgreSQL-compatible ordered-set aggregates:

```sql
PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.loan_amount)
PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY f.income)
```

This preserved the intended median calculation while making the views executable in PostgreSQL 18.

## 20. Power BI semantic model

The Power BI layer is stored as a PBIP project. The semantic model connects to the PostgreSQL-backed analytical model and uses the star-schema relationships.

The semantic model includes reusable measures for:

- Application volume.
- Originated applications.
- Denied applications.
- Approved not accepted applications.
- Withdrawn applications.
- Incomplete applications.
- Origination rate.
- Denial rate.
- Average originated loan amount.
- Median applicant income.

Measures are kept numeric where possible so visual-level display units can control formatting. This avoids converting measures to text with `FORMAT()` and keeps them reusable.

## 21. Existing Power BI pages

The existing Power BI report includes:

1. Lending Executive Overview.
2. Approval & Denial Analysis.

The Executive Overview is designed for leadership-level monitoring, with KPIs and high-level breakdowns. The Approval & Denial Analysis page is more diagnostic, focused on lending outcomes and rate-based comparisons.

Several report refinements were made during development:

- Replaced raw action and loan-purpose codes with business-readable labels.
- Used county names when deterministically available.
- Kept lender LEIs where lender names were not present.
- Fixed display units so application volume renders as values such as `1.16M` instead of malformed suffixes.
- Removed QA-only measures from executive visuals.
- Reworked visual titles into business language.
- Kept QA checks reserved for validation-oriented pages.

## 22. Major bugs/issues encountered and root causes

The project surfaced several realistic data engineering and BI issues:

- Initial batching bug: only 11,292 rows loaded instead of 1,161,292. Root cause was incorrect batching behavior in the first California-only flow.
- Slow staging inserts: pandas and SQLAlchemy multi-row inserts were too slow for large HMDA loads.
- Incomplete `dim_loan` grain: the dimension did not initially preserve enough fields to represent loan-product business grain correctly.
- Geography mismatch: a TX row with null county but populated census tract exposed inconsistent county normalization between dimension and fact logic.
- PostgreSQL median compatibility: `MEDIAN()` was not valid PostgreSQL syntax in this environment.
- Static validation count: validation hard-coded the California-only 1,161,292 expected rows.
- Duplicate validation null behavior: duplicate-source-row validation returned `NULL` when no duplicates existed.
- Power BI numeric formatting: semantic-model suffix formatting caused malformed labels such as duplicated `M` and `K` suffixes.
- PBIR schema issue: an unsupported `$id` property caused a Power BI schema error in a visual object.
- Custom visual mismatch: a chart type was treated as unavailable, requiring replacement with a built-in Power BI visual.

## 23. How each issue was diagnosed and fixed

The initial batching issue was diagnosed by comparing expected source row counts to loaded warehouse counts. The fix focused on preserving chunk boundaries and reconciling total input, valid, and rejected rows.

The slow staging insert problem was diagnosed with timing benchmarks. A 100,000-row load using the original insert path took roughly 18 minutes. The fix replaced batch insertion with PostgreSQL `COPY FROM STDIN`.

The `dim_loan` issue was diagnosed by reviewing the business meaning of loan attributes and checking whether the dimension grain could collapse distinct loan records. The fix expanded the business key to seven fields.

The geography issue was diagnosed by tracing one specific Texas row through staging, dimension population, and fact joins. The fix made `dim_geography` derive county from the first five census tract digits when county is null, matching the fact logic.

The PostgreSQL `MEDIAN()` issue was diagnosed by running the view file against PostgreSQL. The fix replaced `MEDIAN()` with `PERCENTILE_CONT(0.5) WITHIN GROUP`.

The validation hard-code was diagnosed after the warehouse expanded beyond California. The fix made row-count validation compare staging and fact dynamically.

The duplicate validation issue was diagnosed from SQL behavior: an aggregate over no duplicate groups could produce no row or null-like behavior. The fix wrapped duplicate counts in a `COALESCE` expression that returns integer zero.

The Power BI formatting issues were diagnosed by inspecting rendered visuals and PBIR JSON. The fix kept measures numeric with plain model formats and moved display units to individual visuals.

## 24. Performance improvements and benchmark numbers

The most important performance improvement was replacing the staging insert path.

Before optimization:

- Staging used pandas and SQLAlchemy multi-row insert behavior.
- A benchmark for 100,000 rows was roughly 18 minutes.
- During one 2.3M-row load attempt, the original insert path had loaded only 200,000 staging rows before the laptop crashed.

After optimization:

- Staging uses PostgreSQL `COPY FROM STDIN`.
- The COPY benchmark loaded 100,000 rows in 9.788 seconds.
- Throughput was about 10,216 rows per second.
- The benchmark used two 50,000-row batches.
- The benchmark ran inside one explicit transaction and rolled back afterward.

This was a major shift from a prototype loader to a practical warehouse loading path.

## 25. Current verified metrics

Current verified project state:

- Source: HMDA public mortgage data.
- States: CA, TX, FL, NY, IL.
- Years currently loaded: 2023, 2024, and 2025.
- Logical year/state combinations: 15.
- 2023 source file strategy: one yearly multi-state CSV.
- 2024 and 2025 source file strategy: per-state CSV files.
- HMDA schema width: 99 columns.
- PostgreSQL version: PostgreSQL 18.
- Staging rows: 12,006,526.
- Fact rows: 12,006,526.
- Duplicate source rows: 0.
- Null mandatory fact keys: 0.
- Invalid action codes: 0.
- Invalid non-positive loan amounts: 0.
- Unmatched dimension keys: 0.
- Staging-to-fact reconciliation difference: 0.
- ETL pipeline status: completed successfully.
- PostgreSQL views status: created successfully.
- BI layer: Power BI PBIP semantic model and dashboards.

## 26. Evolution from one state to multiple states and years

The original project started as a California-only implementation. That was useful for proving the model, but it created hard-coded assumptions:

- One raw input file.
- One state.
- One expected row count.
- A California-only validation target.

The architecture evolved into a multi-file, multi-state, multi-year pipeline by:

- Replacing hard-coded file paths with source discovery.
- Introducing the `hmda_<YEAR>_<STATE>.csv` naming convention.
- Adding `hmda_<YEAR>_multi_state.csv` support for yearly multi-state source files.
- Validating filename year and state coverage against file contents.
- Failing clearly on ambiguous same-year coverage when multi-state and per-state files both exist.
- Consolidating all valid rows into one Parquet dataset.
- Loading all clean rows into one staging table.
- Keeping the star schema independent of any single state.
- Making row-count validation dynamic.

This changed the project from a single-state dashboard into a scalable warehouse pattern.

## 27. Planned next work

Planned next steps:

- Add richer lender names if a reliable source field or enrichment table is introduced.
- Build the remaining Power BI analytical pages.
- Add a dedicated validation or QA report page for warehouse checks.
- Continue improving business-readable labels and slicers.
- Expand executive and diagnostic reporting without changing the validated warehouse grain.

These are planned enhancements, not completed claims.

## 28. Recruiter and interview talking points

Useful talking points:

- This project demonstrates end-to-end ownership across ETL, warehouse modeling, validation, performance tuning, SQL views, and Power BI.
- The dataset is real, public, large, and messy enough to require production-style design decisions.
- The pipeline evolved from a single-state prototype into a five-state, three-year warehouse with 12,006,526 reconciled fact rows.
- The PostgreSQL load path was optimized with native `COPY FROM STDIN`, improving a 100,000-row benchmark from roughly 18 minutes to under 10 seconds.
- The star schema separates business dimensions from the central application fact table.
- Validation is dynamic and reconciles the current warehouse instead of relying on hard-coded row counts.
- The project includes documented bugs, diagnosis, fixes, and regression tests.
- Power BI measures were kept numeric and reusable, with formatting handled at the visual layer.

## 29. Concise 60-90 second project explanation

This project is an end-to-end lending analytics warehouse and Power BI dashboard built on public HMDA mortgage application data. It started as a California-only pipeline and evolved into a five-state, three-year warehouse covering CA, TX, FL, NY, and IL for 2023 through 2025, with 15 logical year/state combinations and 12,006,526 validated fact rows.

The pipeline discovers raw HMDA files using both per-state and yearly multi-state naming conventions, processes them in pandas chunks, separates rejected rows, writes a consolidated Parquet layer, and bulk-loads PostgreSQL staging using `COPY FROM STDIN`. I then populate a star schema with lender, geography, loan, applicant profile, and action-taken dimensions around a loan application fact table.

The project includes dynamic warehouse validation, analytical SQL views, and a Power BI PBIP semantic model with executive and denial-analysis pages. A major performance improvement was replacing slow SQLAlchemy inserts with PostgreSQL COPY, reducing a 100,000-row staging benchmark from roughly 18 minutes to 9.788 seconds. The current warehouse reconciles 12,006,526 staging rows to 12,006,526 fact rows with zero duplicate source rows, zero unmatched dimension keys, and zero staging-to-fact difference.

## 30. Example STAR-format answer

Question: Tell me about a difficult technical problem you solved.

Situation: I was building a mortgage lending analytics warehouse from public HMDA data. The first version worked for a California-only file, but when I expanded toward a multi-state, multi-year warehouse, the staging load became too slow and the validation logic still assumed a fixed California row count.

Task: I needed to make the pipeline scalable and trustworthy without changing the business grain of the warehouse or breaking the Power BI model.

Action: I benchmarked the staging load and found that pandas and SQLAlchemy multi-row inserts were the bottleneck. A 100,000-row test was taking roughly 18 minutes. I replaced that path with PostgreSQL native `COPY FROM STDIN` using the existing SQLAlchemy and psycopg2 connection, while preserving batch processing, generated staging IDs, load timestamps, profile hashes, explicit column order, and null handling. I also redesigned validation to compare staging and fact dynamically instead of using a hard-coded California count, and added support for yearly multi-state ingestion without double-counting same-year per-state files. Along the way, I fixed a geography edge case where a Texas row had a null county but a valid census tract, making dimension and fact normalization consistent.

Result: The optimized COPY benchmark loaded 100,000 rows in 9.788 seconds at about 10,216 rows per second. The completed warehouse validates 12,006,526 staging rows against 12,006,526 fact rows for the 2023–2025 five-state scope, with zero duplicate source rows, zero unmatched dimension keys, and zero reconciliation difference. The result is a scalable PostgreSQL warehouse and Power BI model with a completed three-year analytical foundation.
