# Phase 2A Geographic Explorer design audit

Audit date: 2026-09-25  
Starting revision: `36afe85` (`checkpoint: verified phase 1 web analytics`)

## Current truth

Phase 1 is an additive Next.js App Router application under `web/`. It uses a
server-only PostgreSQL pool, fixed parameterized queries, Zod request validation,
Apache ECharts, Tailwind CSS, and URL query state. The only enabled route is the
Executive Overview at `/`; the application shell renders the remaining phases as
disabled navigation items.

The established metric definitions remain governed by the Power BI TMDL and
`docs/POWER_BI_REPORTING_LOGIC.md`. Phase 2 must reuse Application Volume as
action codes 1-5, 7, and 8; Credit Decisions as codes 1-3; Originations as code 1;
Denials as code 3; and both rates over Credit Decisions.

The Phase 1 database layer currently contains:

- `analytics.mv_web_executive_metrics`: 168 exact year/state/purpose cube rows,
  including non-additive median income.
- `analytics.mv_web_county_volume`: 9,323 year/state/county/purpose volume rows.
- `analytics.mv_web_lender_volume`: 54,966 year/state/purpose/LEI volume rows.

The county and lender views contain Application Volume only. They cannot support
county decision rates or combined lender/geography filtering without drifting
from the governed populations. The Executive cube cannot be safely joined to
them to infer those metrics.

`analytics.dim_geography` preserves five-character county FIPS codes. It contains
63 distinct county values for California, 70 for Florida, 104 for Illinois, 64
for New York, and 255 for Texas; each state includes one `UNKNOWN` value. The
warehouse contains no county-name or boundary-geometry columns.

## Reusable Phase 1 assets

- PostgreSQL pool configuration and credential isolation in `web/src/lib/server`.
- Canonical year/state constants and metric definitions.
- Zod validation pattern and parameterized API routes.
- `AppShell`, theme toggle, loading/error/empty states, metric formatting,
  `ChartCard`, and the responsive ECharts wrapper.
- URL state through `next/navigation` without another state-management library.
- Existing visual language, breakpoints, focus styles, and accessible chart-table
  disclosure pattern.

## Revised product direction

Phase 2A must establish a coordinated geographic exploration surface rather than
reproducing a Power BI page or the Phase 1 sequence of filters, KPI cards, charts,
and tables. The primary analytical control will be an interactive SVG US map.
Selecting a geography changes the map, breadcrumb, metrics, ranked markets,
contextual observations, and accessible table as one analytical view.

Phase 2B Multi-Year Trends is deliberately excluded from this implementation
pass. Its interaction model will be decided after Phase 2A is verified.

## Smallest justified data change

Add one reference table and one materialized aggregate:

1. `analytics.ref_county` keeps five-character FIPS as its primary key and stores
   the Census county/state names plus representative latitude/longitude.
2. `analytics.mv_web_geography_metrics` stores additive governed action counts at
   year/state/county/LEI grain. The API may safely sum these rows across years,
   counties, states, or lenders and must recompute rates from summed numerators
   and denominators.

This grain supports state-to-county drilldown, lender and year filters, and exact
geographic comparisons without another warehouse or backend. It does not change
facts, dimensions, ETL behavior, validation, or Power BI.

## County-name solution

Use the U.S. Census Bureau 2025 National Counties Gazetteer file. The source is a
pipe-delimited national reference whose `GEOID` is the concatenated state and
county FIPS and whose `NAME` is the human-readable county or equivalent name.
Filter it to CA, FL, IL, NY, and TX; preserve `GEOID` as text; retain the official
state abbreviation, name, and internal-point coordinates; and seed the reference
table. `UNKNOWN` remains an explicit warehouse category and is never assigned a
fabricated county name.

Source:
`https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_counties_national.zip`

Record layout:
`https://www.census.gov/programs-surveys/geography/technical-documentation/records-layout/gaz-record-layouts/gaz25-record-layouts.html`

## Boundary geometry solution

Use the lightweight `us-atlas` preprojected Albers TopoJSON asset as boundary
geometry and `topojson-client` plus `d3-geo` for conversion and SVG path
generation. `us-atlas` is derived from U.S. Census Bureau cartographic boundary
files. Geometry is a presentation asset only: state and county IDs are joined to
validated aggregates through canonical two- and five-character FIPS keys, while
human-readable county names continue to come from `analytics.ref_county`.

This avoids MapLibre, deck.gl, tiles, a map server, and slippy-map interaction.
The geometry dependency is loaded only by the Geographic Explorer route. The
same ranked/table data remains available when the map cannot be used.

## API and page design

- `GET /api/analytics/geography`: validated `year`, `state`, `county`, `lender`,
  and display-metric state; selected-scope KPIs; state or county comparison rows;
  deterministic observations; bounded options.
- `GET /api/analytics/lenders`: bounded, parameterized lender search returning a
  maximum of 20 LEI-grain options.
- `/geography`: interactive US state choropleth, state-to-county drill, breadcrumb
  navigation, selectable volume/origination/denial metric, coordinated scope
  metrics, ranked markets, deterministic “What stands out” observations, and an
  exact accessible table representing the same geography rows.

State and county paths will provide pointer hover, visible keyboard focus,
Enter/Space selection, and a custom tooltip containing the geography name,
selected measure, Application Volume, Credit Decisions, and relevant denominator.
The map uses a wide analytical canvas on desktop and a simplified stacked layout
with a larger touch map plus ranked markets on mobile; it is never the only route
to the data.

State comparison is not a separate mode in this pass. The national map, ranked
markets, and state table already expose comparable state values together, while
selecting one state intentionally transitions to county investigation. A future
comparison mode can be added without changing the API grain if user review shows
it would add value.

## Verification plan

- Unit-test all Phase 2A query-state parsers, dependent state/county rules,
  deterministic observations, and map metric formatting.
- Reconcile API/service output against independent fact/dimension PostgreSQL
  queries for overall, California, Texas, Los Angeles County (`06037`), and one
  lender slice.
- Run the full Python compilation/tests and `load_data.py --validate-only`.
- Run frontend lint, typecheck, unit/integration tests, and production build.
- Inspect the Geographic Explorer at desktop and 390x844, both themes,
  navigation, restored URL state, pointer/keyboard feedback, state-to-county and
  breadcrumb drill, metric switching, invalid/empty/error handling, and console
  output.
- Confirm `git diff -- powerbi` is empty.

## Implemented Phase 2A shape

The implementation followed this design without widening scope. The resulting
materialized view contains 343,715 rows at the documented grain and occupies 83
MB; the Census reference contains 543 official counties or equivalents. The
browser receives five state comparison rows nationally or a bounded county set
for the selected state. Phase 2B remains deferred.
