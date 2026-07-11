# Project Scope

## Business Problem
A bank needs transparent, actionable insights into its mortgage‑lending activity to:
- Monitor approval and denial patterns across demographics and geographies.
- Assess portfolio risk and regulatory compliance.
- Support fair‑lending initiatives and strategic product development.

## Final Project Objectives
1. **Data Integration** – Ingest, clean, and reconcile HMDA loan‑application records.
2. **Descriptive Analytics** – Produce summary statistics on volumes, approval rates, average loan sizes, etc.
3. **Diagnostic Analysis** – Identify drivers of approval/denial (income, loan‑to‑value, debt‑to‑income, race/ethnicity, geography, etc.).
4. **Predictive Insight (optional)** – Build baseline models to predict approval likelihood.
5. **Regulatory Reporting** – Enable extraction of fields required for HMDA reporting and fair‑lending assessments.

## Supported Analytics (based on available HMDA California dataset)
- **Volume & Approval Trends**: Count of applications, approval/denial rates by year (only 2025 in this snapshot).
- **Demographic Analysis**: Approval rates by applicant ethnicity, race, sex, age bands, income brackets, credit‑score type.
- **Geographic Analysis**: Lending volume and approval rates by state (CA), county, census tract, MSA/MD.
- **Loan‑Characteristics Analysis**: Distribution of loan purpose, type, lien status, loan‑to‑value, debt‑to‑income, interest rate, rate spread.
- **Action Analysis**: Breakdown of action_taken (originated, approved‑not‑accepted, denied, withdrawn, incomplete, purchased).
- **High‑Cost Loan Analysis**: Share of loans flagged as higher‑priced (hoepa_status) and associated attributes.
- **Purchaser Analysis**: Distribution of loan purchaser types.
- **Temporal Analysis**: Limited to a single year; trends require multi‑year data.
- **Aggregate Metrics**: Average loan amount, income, LTV, DTI, interest rate, etc., sliceable by any dimension.

## Unsupported Analytics (require additional data or multiple years)
- **Year‑over‑year trends** (only 2025 present).
- **Comparative analysis with market benchmarks** (requires aggregate HMDA data or external industry data).
- **Longitudinal applicant tracking** (no unique applicant identifier across time).
- **Detailed credit‑score modeling** (credit score values not provided, only type).
- **Property‑level characteristics** beyond occupancy, units, and manufactured‑home flags.
- **Cash‑flow or debt‑service‑to‑income** ratios (only DTI available).
- **Behavioral scoring** (no repayment history).

## Recommended Implementation Order
1. **Data Landing** – Place HMDA California CSV (`state_CA.csv`) and any required lookup files (e.g., LEI register, geographic FIPS tables, HMDA code lists) into `data/raw/`.
2. **Ingestion & Staging** – Load the CSV into a staging table in PostgreSQL (or preferred RDBMS) using bulk copy; no transformation yet.
3. **Data Profiling & Validation** – Run row/column counts, verify data types, capture missing‑value percentages; update `docs/data_dictionary.md` and `docs/data_quality_report.md` with actual measurements.
4. **Cleansing & Standardisation** – Replace `NA` strings with true NULLs, trim whitespace, standardize codes (e.g., ensure state_code uppercase).
5. **Dimension Modelling** – Create dimension tables from cleaned staging data:
   - `Dim_Date` (year only for now; can expand with full date if available)
   - `Dim_Applicant` (demographics: ethnicity, race, sex, age, income, credit_score_type)
   - `Dim_Geography` (state, county, census tract, MSA/MD)
   - `Dim_Loan` (loan purpose, type, lien status, loan amount, LTV, DTI, interest rate, rate spread, etc.)
   - `Dim_Action` (action_taken, purchaser_type, preapproval)
   - Additional lookup dimensions for categorical fields (ethnicity, race, loan purpose, etc.) using official HMDA code tables.
6. **Fact Table Population** – Build `Fact_LoanApplication` with foreign keys to the dimensions and additive measures: loan_amount, income, loan_to_value_ratio, debt_to_income_ratio, interest_rate, rate_spread, total_loan_costs, total_points_and_fees, origination_charges, discount_points, lender_credits, loan_term, etc.
7. **Aggregates & Indexing** – Create monthly/quarterly aggregate tables for performance; index foreign keys and date key.
8. **BI Layer** – Connect Power BI (`powerbi/`) to the star schema; develop measures matching the KPI list below.
9. **Report Development** – Build the six dashboard pages outlined in the README:
   1. Loan Application Overview
   2. Approval and Denial Analysis
   3. Borrower Demographics
   4. Geographic Lending Distribution
   5. Lender Performance Metrics
   6. Portfolio Trends & Risk Indicators
10. **Validation & QA** – Reconcile report totals with raw‑data totals; verify referential integrity; spot‑check sampled records.
11. **Documentation & Hand‑off** – Update `docs/` with final data dictionary, data‑quality report, ETL/SQL scripts (if later phases require them), and model diagrams.

## Key Performance Indicators (KPIs) (as measures)
| KPI | Description | Suggested Calculation |
|-----|-------------|-----------------------|
| Application Volume | Count of loan applications | `COUNT(*)` |
| Approved Loans | Count of loans with action_taken = 1 (originated) | `COUNT(CASE WHEN action_taken = 1 THEN 1 END)` |
| Approval Rate | % of applications originated | `COUNT(CASE WHEN action_taken = 1 THEN 1 END) * 1.0 / COUNT(*)` |
| Denial Rate | % of applications denied (action_taken = 3) | `COUNT(CASE WHEN action_taken = 3 THEN 1 END) * 1.0 / COUNT(*)` |
| Withdrawal Rate | % of applications withdrawn (action_taken = 4) | `COUNT(CASE WHEN action_taken = 4 THEN 1 END) * 1.0 / COUNT(*)` |
| Incomplete Rate | % of files closed for incompleteness (action_taken = 5) | `COUNT(CASE WHEN action_taken = 5 THEN 1 END) * 1.0 / COUNT(*)` |
| Purchased Loans | Count of loans purchased by institution (action_taken = 6) | `COUNT(CASE WHEN action_taken = 6 THEN 1 END)` |
| Average Loan Amount | Mean loan amount for originated loans | `AVG(CASE WHEN action_taken = 1 THEN loan_amount END)` |
| Median Applicant Income | Median income of applicants | `MEDIAN(CASE WHEN applicant_id IS NOT NULL THEN income END)` (approximate via PERCENTILE_CONT) |
| Average LTV | Mean loan‑to‑value ratio | `AVG(loan_to_value_ratio)` (excluding NULL) |
| Average DTI | Mean debt‑to‑income ratio | `AVG(debt_to_income_ratio)` |
| Average Interest Rate | Mean interest rate | `AVG(interest_rate)` |
| Average Rate Spread | Mean rate spread | `AVG(rate_spread)` |
| High‑Cost Loan Share | % loans flagged as higher‑priced (hoepa_status = 1) | `SUM(CASE WHEN hoepa_status = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*)` |
| Geographic Concentration (Top 5 MSAs) | % of total loan amount in top 5 MSAs | `SUM(CASE WHEN derived_msa-md IN (SELECT top 5 derived_msa-md FROM Fact_LoanApplication GROUP BY derived_msa-md ORDER BY SUM(loan_amount) DESC) THEN loan_amount END) / SUM(loan_amount)` |
| Demographic Shares | % of applications by ethnicity/race/sex/age band | `COUNT(CASE WHEN derived_ethnicity = 1 THEN 1 END) * 1.0 / COUNT(*)`, etc. |
| Income‑Category Share | % of applicants below area median income (if AMI data available) – requires external lookup. |

## Suggested Power BI Visualisations
- **Slicers**: Year (if multiple years added), state, county, ethnicity, race, sex, loan type, loan purpose, action taken, purchaser type.
- **Cards**: KPI totals (applications, approved, denied, avg loan amount, avg income, etc.).
- **Bar/Column Charts**: Application volume by geography, approval rate by demographic group.
- **Stacked Bar**: Distribution of loan purpose, loan type, lien status.
- **Scatter Plot**: Loan amount vs. applicant income (colored by approval status).
- **Map (Filled)**: Loan density or approval rate by census tract or county (requires geographic coordinates).
- **Funnel Chart**: Application flow (received → approved → originated → purchased).
- **Tooltips**: Show detailed loan‑level attributes (e.g., loan amount, income, LTV, DTI, interest rate) when hovering over a visual.
- **Drillthrough Pages**:
  - From summary to **Loan Detail** tab showing all fields for a selected application (or aggregated to applicant level).
  - From geographic shape to **Geography Detail** showing breakdowns by demographic and loan characteristics.
- **Title & Navigation**: Consistent header with report title, date refreshed, and navigation pane.

## Data Validation Strategy
- Confirm row count after load matches source file (1,161,292).
- Validate that numeric fields contain only numbers or NULL.
- Validate that coded fields fall within defined enumerations (compare to HMDA code lists).
- Ensure referential integrity between fact and dimension tables (no orphaned foreign keys).
- Reconcile sums of numeric measures (e.g., total loan amount) between fact table and aggregate tables.
- Spot‑check a random sample of records against the original CSV for accuracy.
- Document any transformation rules applied (e.g., handling of `NA` as NULL).

## Assumptions
- The provided `state_CA.csv` represents the bank’s HMDA‑reportable loan applications for California in 2025.
- Public HMDA lookup files (e.g., for ethnicity, race, loan purpose, etc.) are freely available from the CFPB/FFIEC website and can be incorporated as dimension tables.
- No personally identifiable information beyond what is already disclosed in the public HMDA file is present.
- The analysis will be limited to the supplied calendar year unless additional yearly files are added later.

## Open Items / Next Steps
- Obtain any required HMDA lookup files (e.g., `action_taken.csv`, `loan_purpose.csv`, etc.) and place them in `data/raw/lookup/`.
- If multi‑year analysis is desired, obtain additional state CSVs for prior years and append to the fact table with appropriate partitioning.
- Consider augmenting with external data sources (e.g., HMDA aggregate data, census socioeconomic data, mortgage‑rate indices) for richer context.

## Estimated Effort (Indicative)
- Data load & staging: 0.5‑1 day
- Dimension & fact modelling: 1‑2 days
- ETL/ELT pipeline (if scheduled): 0.5‑1 day
- Power BI development: 2‑3 days
- Testing, validation, documentation: 1‑2 days
- Total: ~5‑9 working days (subject to resource availability and familiarity with the HMDA schema).

---
*This scope is based solely on the profiling of the `state_CA.csv` file. Should additional data sources or alternative requirements emerge, the scope should be revisited accordingly.*