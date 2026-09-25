# Web analytics Phase 1 implementation report

Implementation date: 2026-09-25  
Scope: application shell and Executive Overview

## Outcome

Phase 1 adds a responsive Next.js analytics product alongside the existing HMDA
engineering stack. It does not replace or modify the ETL, star schema, validation
queries, governed Power BI measures, semantic model, or report pages.

The Executive Overview includes global year, state, and loan-purpose filters;
URL-persisted filter state; linked year, purpose, and state charts; accessible
chart data tables; outcome, lender, and county summaries; responsive navigation;
dark/light themes; and explicit loading, empty, and error states.

## Files added or changed

- `web/`: Next.js 15, React 19, TypeScript, Tailwind CSS 4, Apache ECharts,
  Lucide, Zod, PostgreSQL, Vitest, and ESLint application.
- `sql/09_create_web_analytics_views.sql`: exact materialized aggregates for the
  Executive KPI cube, county volume, and LEI-grain lender volume.
- `docs/WEB_ANALYTICS_AUDIT.md`: pre-implementation architecture, semantics,
  validation, testing, and performance audit.
- `docs/WEB_PHASE1_IMPLEMENTATION.md`: this report.
- `README.md`: local web setup and architecture entry point.
- `.gitignore`: frontend build, dependency, coverage, local environment, and test
  temp outputs.

No files under `powerbi/` were changed.

## Architecture

The UI is a client-side analytical workspace inside the Next.js App Router. A
single fixed API route validates filters with Zod and calls server-only,
parameterized PostgreSQL queries. There is no raw SQL endpoint and no database
configuration is included in the browser bundle.

The API reads only the rows needed for the active view: one KPI aggregate, a
small trend series, purpose and state comparisons, and eight ranked lenders and
counties. Business calculations remain server-side. ECharts is dynamically
loaded in the browser and exposes ARIA descriptions plus disclosure tables for
keyboard and screen-reader access.

## Trusted queries and views

Metric definitions are copied from the governed Power BI TMDL and
`docs/POWER_BI_REPORTING_LOGIC.md`, not inferred from visual titles. Application
Volume excludes action code 6; Credit Decisions use codes 1-3; origination and
denial rates divide by Credit Decisions; average originated loan amount is
restricted to action code 1; applicant income retains the HMDA thousands unit.

Existing warehouse dimensions and `fact_loan_application` feed three new
materialized views:

- `analytics.mv_web_executive_metrics`: exact cube across year, state, and loan
  purpose, including exact median income for every supported scope.
- `analytics.mv_web_county_volume`: application volume at year/state/county/
  purpose grain.
- `analytics.mv_web_lender_volume`: application volume at
  year/state/purpose/LEI grain with official lender-name enrichment.

The views were created against the local 12,006,526-row warehouse. Total size was
approximately 11.6 MB, and a two-scope lookup including connection setup completed
in 0.204 seconds, compared with 18.059 seconds for the unfiltered raw-fact KPI and
median query observed during the audit.

Refresh all three materialized views after a successful warehouse refresh using
the commands documented at the top of `sql/09_create_web_analytics_views.sql`.

## Validation performed

- Python compilation over every tracked Python entry point, source module,
  script, and test: passed after implementation.
- `python -m pytest -v --basetemp=.pytest-tmp`: 43 tests passed after
  implementation in 9.91 seconds.
- `python load_data.py --validate-only`: all 13 warehouse checks passed, including
  12,006,526 staging/fact rows, zero duplicate or missing source mappings, zero
  orphaned dimensions, and zero source-value mismatches.
- Frontend ESLint: passed with no warnings.
- TypeScript `tsc --noEmit`: passed.
- Vitest: 11 tests passed across filter validation, injection-like inputs,
  URL serialization, and metric formatting.
- Next.js production build: passed; `/` is statically rendered and the analytics
  API remains a dynamic Node.js route.
- API input checks: unsupported year and injection-like state filters returned
  HTTP 400.
- Live reconciliation: the API exactly matched the direct PostgreSQL/Power BI
  baseline for both the all-data view and California 2025, including counts,
  rates, average originated loan amount, and median applicant income.
- Browser QA: inspected desktop and 390x844 mobile layouts, mobile navigation,
  light/dark themes, URL-persisted filters, California 2025 results, the invalid
  filter error state, and browser console output. No console errors were present.

## Known limitations

- Phase 1 exposes only the Executive Overview; later navigation entries are
  clearly disabled and labeled with their planned phase.
- County display uses state and five-digit FIPS because county names are not
  present in the current warehouse.
- The materialized views require an explicit refresh after the warehouse changes.
- Lender search, lender profiles/comparison, maps, and borrower/denial drilldowns
  are intentionally deferred to their requested phases.
- The loading and empty-state components are implemented and code-reviewed; the
  local aggregate returned too quickly to hold the loading state for a stable
  screenshot, and all supported filter combinations currently contain data.

## Recommended Phase 2

1. Add the Geographic Explorer using state-to-county drilldown. Begin with a
   lightweight vector map only if county geometry and bundle cost justify it;
   otherwise use a ranked analytical table plus focused map loading.
2. Add Multi-Year Trends with percentage-point rate changes and relative
   application-volume year-over-year changes from the established Power BI
   measures.
3. Extend the aggregate layer with exact state/county trend and outcome measures,
   preserving the same decision denominators and avoiding client-side rollups of
   non-additive statistics.
4. Add contract tests for new API responses, URL-driven drill state, keyboard
   chart interactions, and no-data combinations before widening the supported
   filter domain.
