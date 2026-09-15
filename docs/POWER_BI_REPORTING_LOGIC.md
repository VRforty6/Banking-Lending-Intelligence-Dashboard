# Power BI Reporting Logic

This note documents the reporting definitions used by the Power BI semantic model. It is intentionally limited to report-facing logic and does not change the PostgreSQL warehouse grain, ETL, or source data.

## HMDA action-code populations

The semantic model separates HMDA records into four related populations:

| Population | Action codes | Definition |
|---|---|---|
| Total HMDA Records | 1, 2, 3, 4, 5, 6, 7, 8 | Every valid HMDA source record loaded to the fact table. |
| Application Volume | 1, 2, 3, 4, 5, 7, 8 | Application and preapproval records, excluding purchased loans. |
| Purchased Loans | 6 | Purchased loans reported under HMDA action taken code 6. |
| Credit Decisions | 1, 2, 3 | Completed application decisions: originated, approved not accepted, or denied. Preapproval outcomes are reported separately and are not included in this denominator. |

Rate denominators:

- `Origination Rate` = `Originated Applications` / `Credit Decisions`.
- `Denial Rate` = `Denied Credit Decisions` / `Credit Decisions`.
- `Denied Credit Decisions` = `Denied Applications` (action code 3).
- `Withdrawal Rate` and `Incomplete Rate` remain application-process rates and use `Application Volume`.

Outcome-distribution visuals that need to show purchased loans use `Total HMDA Records`. Volume, trend, state, lender, borrower, and loan-purpose visuals use `Application Volume` so purchased loans are not mixed into application analysis.

HMDA `income` values are reported in thousands of dollars (for example, reported value `50` represents $50,000). The semantic model therefore keeps the stored numeric value and formats income measures with a `K` suffix; it does not multiply the warehouse value by 1,000.

## Lender ranking and duplicate names

Lender grouping remains at the unique LEI grain. `Lender Display` shows the official lender name when available and falls back to LEI when no official name was matched.

When more than one LEI has the same official lender name, the display label appends the last six LEI characters. This preserves readable names while preventing duplicate names from collapsing separate LEIs in visuals.

Top-N lender membership is ranked by application volume at the LEI grain. Ranking respects slicers, but removes the current chart segment filters for state and loan purpose so stacked chart segments use the same Top-N lender population. Ties are broken deterministically by LEI in ascending lexical order, so Top 10 and Top 15 return fixed membership counts rather than expanding at the cutoff.

## Race labels and multiple reported races

`Applicant Race Label` uses one broad reporting grain across all five applicant race fields. It is applicant-only and does not combine applicant and co-applicant race. The source codes map as follows:

- 1: American Indian or Alaska Native
- 2 and 21–27: Asian
- 3: Black or African American
- 4 and 41–44: Native Hawaiian or Other Pacific Islander
- 5: White
- 6: Information not provided
- 7: Not applicable
- blank or an unsupported code: Unknown

One populated broad race group returns that group, including when multiple populated fields contain codes within the same broad group. `Multiple races reported` is used only when populated applicant fields span more than one mapped label. Codes 6 and 7 remain explicit labels and are not merged into a race group. The current project data contains no records that combine either status code with another populated applicant race field; an unsupported populated code resolves to `Unknown` rather than being assigned to an unsupported group.

Sources for race-code behavior:

- CFPB Regulation C Appendix B: https://www.consumerfinance.gov/rules-policy/regulations/1003/b/
- CFPB HMDA modified LAR data dictionary: https://github.com/cfpb/hmda-platform/blob/master/docs/spec/markdown/modified_lar/2021_Modified_LAR_Data_Dictionary.md

## Year-over-year measures

Year-over-year comparisons use the latest application year in the current filter context and compare it to the prior year:

- `Application Volume YoY %` is a relative percent change.
- `Origination Rate YoY Change` is a percentage-point change.
- `Denial Rate YoY Change` is a percentage-point change.

The model includes `YoY Comparison Years` so Power BI tooltips can show the comparison pair, such as `2025 vs 2024`.
