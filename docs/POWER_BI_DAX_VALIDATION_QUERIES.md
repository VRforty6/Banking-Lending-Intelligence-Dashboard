# Power BI DAX validation queries

Run these queries in DAX Query View against the report semantic model. The expected values below are assertions supplied from the PostgreSQL reconciliation; this file does not claim that the filtered queries were executed in this repository.

## 1. 2025 California decision-rate check

```dax
EVALUATE
CALCULATETABLE (
    ROW (
        "Credit decisions", [Credit Decisions],
        "Origination rate", [Origination Rate],
        "Denial rate", [Denial Rate]
    ),
    TREATAS ( { 2025 }, 'analytics fact_loan_application'[application_year] ),
    TREATAS ( { "CA" }, 'analytics dim_geography'[state_code] )
)
```

Expected result: `791639`, `0.722890`, `0.224045` (72.2890% and 22.4045%). The unallocated decision share is approved-not-accepted because the rate denominator is action codes 1–3: `1 - [Origination Rate] - [Denial Rate]`.

## 2. Consistent Top-15 LEI membership

This returns the selected Top-15 population once, then displays all volume, rate, and originated-amount measures for exactly those LEIs. Keep any report-equivalent year, state, or purpose filters in the marked filter block.

```dax
DEFINE
    VAR __LenderRows =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            'analytics dim_lender'[Lender Display],
            // Optional filter examples:
            // TREATAS ( { 2025 }, 'analytics fact_loan_application'[application_year] ),
            // TREATAS ( { "CA" }, 'analytics dim_geography'[state_code] ),
            "Top-15 rank", [Lender Application Volume Rank],
            "Applications", [Application Volume Top 15 Lenders],
            "Origination rate", [Origination Rate Top 15 Lenders],
            "Denial rate", [Denial Rate Top 15 Lenders],
            "Average originated amount", [Average Originated Loan Amount Top 15 Lenders]
        )
    VAR __Top15 =
        FILTER ( __LenderRows, [Top-15 rank] <= 15 )
EVALUATE
    __Top15
ORDER BY
    [Top-15 rank],
    'analytics dim_lender'[lei]
```

Pass criteria: 15 rows; ranks 1–15; the same LEIs populate volume, both rates, and originated amount. A blank amount is only acceptable when that LEI has no originated loans in the selected context; it does not change membership.

## 3. Top-10 lender state reconciliation

```dax
DEFINE
    VAR __Ranked =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            // Apply the same year/purpose/state-page filters here when needed.
            "Top-10 rank", [Lender Application Volume Rank]
        )
    VAR __Top10Leis =
        SELECTCOLUMNS (
            FILTER ( __Ranked, [Top-10 rank] <= 10 ),
            "LEI", 'analytics dim_lender'[lei]
        )
    VAR __LenderTotals =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            TREATAS ( __Top10Leis, 'analytics dim_lender'[lei] ),
            "Lender applications", [Application Volume Top 10 Lenders]
        )
    VAR __StateRows =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            'analytics dim_geography'[State Display],
            TREATAS ( __Top10Leis, 'analytics dim_lender'[lei] ),
            "Segment applications", [Application Volume Top 10 Lenders]
        )
    VAR __StateTotals =
        GROUPBY (
            __StateRows,
            'analytics dim_lender'[lei],
            "State segment sum", SUMX ( CURRENTGROUP (), [Segment applications] )
        )
    VAR __Check =
        NATURALLEFTOUTERJOIN ( __LenderTotals, __StateTotals )
EVALUATE
    ADDCOLUMNS (
        __Check,
        "Variance", [State segment sum] - [Lender applications]
    )
ORDER BY
    'analytics dim_lender'[lei]
```

## 4. Top-10 lender purpose reconciliation

```dax
DEFINE
    VAR __Ranked =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            // Apply the same year/state/purpose-page filters here when needed.
            "Top-10 rank", [Lender Application Volume Rank]
        )
    VAR __Top10Leis =
        SELECTCOLUMNS (
            FILTER ( __Ranked, [Top-10 rank] <= 10 ),
            "LEI", 'analytics dim_lender'[lei]
        )
    VAR __LenderTotals =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            TREATAS ( __Top10Leis, 'analytics dim_lender'[lei] ),
            "Lender applications", [Application Volume Top 10 Lenders]
        )
    VAR __PurposeRows =
        SUMMARIZECOLUMNS (
            'analytics dim_lender'[lei],
            'analytics dim_loan'[Loan Purpose Label],
            TREATAS ( __Top10Leis, 'analytics dim_lender'[lei] ),
            "Segment applications", [Application Volume Top 10 Lenders]
        )
    VAR __PurposeTotals =
        GROUPBY (
            __PurposeRows,
            'analytics dim_lender'[lei],
            "Purpose segment sum", SUMX ( CURRENTGROUP (), [Segment applications] )
        )
    VAR __Check =
        NATURALLEFTOUTERJOIN ( __LenderTotals, __PurposeTotals )
EVALUATE
    ADDCOLUMNS (
        __Check,
        "Variance", [Purpose segment sum] - [Lender applications]
    )
ORDER BY
    'analytics dim_lender'[lei]
```

Pass criteria for both Top-10 queries: exactly the same ten LEIs in each result and `Variance = 0` for every lender. Do not include an active filter on the breakdown column itself when testing full reconciliation.

## Applicant race grouping validation

`Applicant Race Label` now uses the same broad reporting grain for single-code and multi-code responses across all five applicant race fields. The allowed output labels are the five broad race groups, `Multiple races reported`, `Information not provided`, `Not applicable`, and `Unknown`. Detailed Asian and Pacific Islander subcategory labels must not appear in the reporting dimension.

```DAX
DEFINE
    VAR __AllowedLabels =
        {
            "American Indian or Alaska Native",
            "Asian",
            "Black or African American",
            "Native Hawaiian or Other Pacific Islander",
            "White",
            "Multiple races reported",
            "Information not provided",
            "Not applicable",
            "Unknown"
        }
    VAR __ActualLabels =
        CALCULATETABLE (
            VALUES ( 'analytics dim_applicant_profile'[Applicant Race Label] ),
            REMOVEFILTERS ()
        )
EVALUATE
    EXCEPT ( __ActualLabels, __AllowedLabels )
```

Pass criterion: zero rows. A non-empty result identifies an unsupported or mixed-grain display label that requires investigation.

Use this reconciliation query to inspect the population rendered by the Borrower Segmentation race visual:

```DAX
EVALUATE
    SUMMARIZECOLUMNS (
        'analytics dim_applicant_profile'[Applicant Race Label],
        "Applications", [Application Volume],
        "Credit decisions", [Credit Decisions],
        "Origination rate", [Origination Rate],
        "Denial rate", [Denial Rate]
    )
ORDER BY
    'analytics dim_applicant_profile'[Applicant Race Label]
```
