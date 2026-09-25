# Web analytics application audit

Audit date: 2026-09-25  
Repository revision: `5eb001b` (`main`)  
Scope: source-of-truth review completed before the Phase 1 web application implementation.

## Current architecture

The repository is an end-to-end HMDA analytics project with four established layers:

1. Public HMDA Loan/Application Register CSV files are processed by the canonical
   `etl_hmda.py` pipeline in 100,000-row chunks.
2. Valid and rejected records are written to Parquet with source-, year-, and
   state-level reconciliation. Raw and generated large data files are intentionally
   excluded from Git.
3. `load_data.py` bulk-loads PostgreSQL staging through `COPY FROM STDIN`, builds a
   dimensional warehouse, creates analytical views, and executes warehouse
   validation. `etl_hmda.py` and `load_data.py` are the current entry points; the
   older `src.main` flow is not the canonical rebuild path.
4. The Power BI PBIP project imports the PostgreSQL star schema and applies the
   governed report measures documented in `docs/POWER_BI_REPORTING_LOGIC.md`.

The web product must sit alongside the fourth layer. It must query PostgreSQL on
the server and must not replace the ETL, warehouse, validation, or Power BI model.

## PostgreSQL model

### Schemas and tables

| Schema | Object | Grain / purpose |
|---|---|---|
| `staging` | `hmda_raw` | One loaded HMDA source row; 99 source fields plus `stg_row_id`, load timestamp, and profile hash. |
| `analytics` | `fact_loan_application` | One row per valid staging record, keyed to all five dimensions. |
| `analytics` | `dim_lender` | One row per LEI, with optional official lender name. |
| `analytics` | `dim_geography` | One row per state/county/census-tract business key. |
| `analytics` | `dim_loan` | One row per seven-field loan-product business key. |
| `analytics` | `dim_applicant_profile` | One row per stable applicant-profile hash. |
| `analytics` | `dim_action_taken` | One row per HMDA action code 1-8. |

The fact table has individual indexes on lender, geography, loan, applicant,
action, and application year foreign keys. Geography has a unique composite index
on `(state_code, county_code, census_tract)`. There are no composite fact indexes
covering the web filter combination of year, state, and loan purpose.

### Existing analytical views

`sql/05_create_views.sql` creates:

- `analytics.vw_lending_overview`
- `analytics.vw_application_outcomes`
- `analytics.vw_borrower_analysis`
- `analytics.vw_geographic_analysis`
- `analytics.vw_lender_performance`
- `analytics.vw_data_quality`

These views are reusable for lineage and basic summaries, but they predate the
final Power BI reporting semantics. In particular, their counts and averages do
not consistently exclude purchased loans or use the credit-decision denominator.
They therefore cannot be used directly for the web KPI layer without preserving
the newer measure definitions below.

## Governed business metrics

The Power BI TMDL and `docs/POWER_BI_REPORTING_LOGIC.md` are the controlling
sources for report-facing definitions. Chart names are not used as definitions.

| Metric | Exact established definition |
|---|---|
| Total HMDA Records | Count of all valid fact rows with action codes 1-8. |
| Application Volume | Total HMDA Records where action code is not 6; equivalently codes 1, 2, 3, 4, 5, 7, and 8. |
| Purchased Loans | Action code 6. |
| Credit Decisions | Action codes 1, 2, and 3. |
| Originated Applications / Originations | Action code 1. |
| Approved Not Accepted Applications | Action code 2. |
| Denied Applications / Denied Credit Decisions | Action code 3. |
| Origination Rate | Originated Applications divided by Credit Decisions. |
| Denial Rate | Denied Credit Decisions divided by Credit Decisions. |
| Withdrawal Rate | Action code 4 divided by Application Volume. |
| Incomplete Rate | Action code 5 divided by Application Volume. |
| Average Originated Loan Amount | Average fact `loan_amount` restricted to action code 1. |
| Average Applicant Income | Average fact `income`; HMDA stores income in thousands of dollars and the semantic model displays a `K` suffix without multiplying the stored value. |
| Median Applicant Income | Median fact `income`, with the same thousands-of-dollars display convention. This is the applicant-income KPI used on the Executive Overview. |
| Distinct Lenders | Distinct LEIs, not distinct display names. |
| Distinct Counties | Distinct `county_code` in the active filter context. |
| State metrics | The same measures after the state dimension filter is applied. |
| County metrics | The same measures at the state/county dimension grain. County display currently uses `STATE - FIPS`; the warehouse does not contain county names. |
| Lender metrics | The same measures at unique LEI grain. Official names are display enrichment only. Duplicate official names append the last six LEI characters. |

Preapproval outcomes 7 and 8 remain in Application Volume but are excluded from
Credit Decisions. Borrower comparisons are descriptive and do not establish
causation or discrimination.

`sql/07_business_queries.sql` contains useful query examples but is not the final
semantic authority: its legacy approval and denial rates divide by all fact rows.
The web API must not reuse those legacy denominators.

## Power BI implementation

The PBIP report contains six 1920x1080 pages in this order:

1. Lending Executive Overview
2. Approval & Denial Analysis
3. Multi-Year Lending Trends
4. State Comparison
5. Lender Performance
6. Borrower Segmentation

The Executive Overview uses Application Volume, Origination Rate with Credit
Decisions context, Denial Rate with Credit Decisions context, Average Originated
Loan Amount, Median Applicant Income, Total HMDA Records by action, Application
Volume by loan purpose, top counties, and top lenders.

The semantic model also defines deterministic LEI-grain Top 10/15 lender ranking,
relative application-volume year-over-year change, and percentage-point
origination/denial changes. Dimension-to-fact relationships are single direction.

The Phase 1 web product will preserve these measures but use a web-native layout
and interaction model instead of reproducing the PBIX canvas.

## Validation and tests

### ETL validation

`etl_hmda.py` validates supported years (2023-2025), supported states (CA, TX,
FL, NY, IL), required fields, action codes 1-8, numeric coercion, positive loan
amounts, and source filename/content consistency. It writes rejected rows with
reasons and enforces `input = valid + rejected` reconciliation.

### Warehouse validation

`sql/06_validation_queries.sql`, executed by `load_data.py --validate-only`, checks:

- staging and fact row-count equality and non-empty staging;
- staging primary-key integrity;
- null mandatory fact keys and invalid action/loan-amount values;
- unmatched dimension keys;
- duplicate fact mappings for a staging row;
- staging rows missing fact mappings;
- fact mappings to unknown staging rows; and
- fact/source year, loan amount, and income mismatches.

The tracked validation report records the earlier core reconciliation checks as
passing. The README accurately notes that the four newer one-to-one mapping/value
checks were added after that report and had not yet been executed against the full
warehouse. They must not be described as historically verified until the live
validation command succeeds.

### Automated tests

Pytest collects 43 unit tests covering lender-name enrichment, numeric conversion,
action validation, rejected-row reasons, reconciliation, Windows file release,
multi-file and multi-state discovery, scope/year/state mismatches, PostgreSQL COPY,
geography fallback, dynamic validation SQL, transaction rollback, and connection
URL escaping. `tests/data_quality/test_dq.py` is a manual sample runner rather than
a pytest test function.

Pre-change verification on 2026-09-25:

- Python compile: passed when run in the writable worktree.
- Python tests: `43 passed in 7.81s` using a repository-local pytest temp root.

## Data volume and performance

Verified warehouse facts and source reconciliation cover 12,006,526 records,
three years, five states, and 15 logical state/year combinations. The local
database reports approximately 1.93 GB for the fact table and 6.15 GB for staging.
The processed Parquet file is approximately 492 MB. The lender dimension contains
3,783 LEIs, including 3,712 official names and 71 LEI fallbacks.

A live unfiltered query that calculated the Executive KPI population and exact
median income from the fact table took 18.059 seconds. A 2025 California decision
rate query took 4.591 seconds. Sending raw fact data to the browser is therefore
both unnecessary and too expensive for an interactive product.

The Phase 1 API should use bounded, parameterized server-side queries over
purpose-built exact aggregates. Exact median income is non-additive, so it must be
precomputed for supported filter combinations rather than averaged from subgroup
medians. Detail rankings can use separate county and lender aggregate grains.

## Live metric reconciliation baseline

The following values were queried directly from PostgreSQL with the exact Power BI
population rules on 2026-09-25:

| Scope | Metric | Value |
|---|---|---:|
| All years/states/purposes | Total HMDA Records | 12,006,526 |
| All years/states/purposes | Application Volume | 10,471,829 |
| All years/states/purposes | Credit Decisions | 8,189,970 |
| All years/states/purposes | Originations | 5,710,620 |
| All years/states/purposes | Denials | 2,123,781 |
| All years/states/purposes | Origination Rate | 69.726995% |
| All years/states/purposes | Denial Rate | 25.931487% |
| All years/states/purposes | Average Originated Loan Amount | $414,462.1127 |
| All years/states/purposes | Median Applicant Income | $117K |
| 2025 California | Application Volume | 1,026,242 |
| 2025 California | Credit Decisions | 791,639 |
| 2025 California | Originations | 572,268 |
| 2025 California | Denials | 177,363 |
| 2025 California | Origination Rate | 72.2890105% |
| 2025 California | Denial Rate | 22.4045303% |

The 2025 California credit-decision and rate values reconcile to the documented
Power BI validation baseline.

## Phase 1 implementation boundary

Phase 1 will add a Next.js/React/TypeScript application shell and an Executive
Overview backed by a thin, validated PostgreSQL API. It may add exact analytical
materialized views and their refresh script, but it will not alter the existing
fact/dimension tables, ETL entry points, validation SQL, Power BI semantic model,
or report files. Navigation entries for later phases will be present but clearly
marked as upcoming rather than implemented with placeholder analytics.
