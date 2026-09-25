# Phase 2A Geographic Explorer implementation report

Implementation date: 2026-09-25  
Phase 1 checkpoint: `36afe85` (`checkpoint: verified phase 1 web analytics`)

## Scope and outcome

Phase 2A is implemented as an additive Geographic Explorer at `/geography`.
Phase 2B was deliberately not implemented. The existing ETL, star schema,
validation SQL, business definitions, and Power BI/PBIP files were not changed.

The page is a coordinated analytical surface rather than a sequence of generic
charts. A local SVG choropleth is the primary state/county selector. Selection
updates the breadcrumb, URL, scoped metrics, ranked comparison, selected outline,
and deterministic “What stands out” narrative. The ranked table exposes the same
important data without requiring a map.

## Architecture changes

- Added `analytics.ref_county`, keyed by five-character county FIPS.
- Added `analytics.mv_web_geography_metrics` at
  year/state/county/LEI grain with additive governed action counts.
- Added bounded, parameterized APIs for geographic analytics and lender search.
- Added the `/geography` App Router page and enabled it in the existing shell.
- Added a route-local SVG renderer over a checked-in preprojected TopoJSON asset.
- Reused the Phase 1 PostgreSQL pool, Zod validation, URL state, theme, formatting,
  loading/error/empty patterns, Tailwind styling, and established metrics.

No ORM, state-management framework, map server, tile service, new database, or
backend service was introduced.

## Data/model changes

`sql/10_create_phase2_geography.sql` creates the reference table and the new
materialized aggregate. The aggregate contains 343,715 rows and occupies 83 MB
in the verified local warehouse. It preserves these reporting populations:

- Total HMDA Records: valid action codes 1–8.
- Application Volume: action code is not 6 (codes 1–5, 7, and 8).
- Credit Decisions: action codes 1–3.
- Originations: action code 1.
- Denials: action code 3.
- Origination Rate: Originations / Credit Decisions.
- Denial Rate: Denials / Credit Decisions.

Rates are recomputed after summing their numerator and denominator; rate values
are never summed or averaged. The browser receives only aggregate state or county
rows for the active view.

## County-name and boundary solution

Human-readable names come from the U.S. Census Bureau 2025 National Counties
Gazetteer. `scripts/generate_county_reference_sql.py` validates the expected
state counts, uniqueness, and five-character GEOID format before generating
`sql/generated/10_county_reference_seed.sql`.

- Official source: `2025_Gaz_counties_national.zip` from `census.gov`.
- Extracted-source SHA-256:
  `1914f0d83243362de83b8ddd298c213b1768d63d62d19464743289abd8bb35b1`.
- Transformation: filter USPS to CA, FL, IL, NY, and TX; preserve GEOID as text;
  retain official name and representative latitude/longitude.
- Loaded reference rows: 543 (CA 58, FL 67, IL 102, NY 62, TX 254).

FIPS remains the canonical join key. Warehouse `UNKNOWN` values are labeled
“County not reported.” Cross-state/anomalous FIPS values remain visible as
“Unmapped county (FIPS)” instead of being silently dropped or relabeled.

The checked-in `counties-albers-10m.json` boundary asset is from `us-atlas` 3,
which redistributes simplified U.S. Census Bureau 2017 cartographic boundary
shapefiles as preprojected Albers TopoJSON. Geometry is presentation-only and is
joined to analytics exclusively by canonical state/county FIPS.

## Endpoints and security

- `GET /api/analytics/geography`: accepts validated `year`, `state`, `county`,
  `lender`, and `metric` parameters and returns the selected scope plus one
  bounded state/county comparison set.
- `GET /api/analytics/lenders`: accepts an at-most-80-character search string and
  returns at most 20 LEI-grain matches.

All SQL is fixed and parameterized. County requires a supported state; year,
state, county, LEI, and metric values are allowlisted or format-validated. There
is no raw SQL endpoint and no database credential enters the client bundle.
An injection-like state filter returned HTTP 400 in both API and browser tests.

## Reconciliation evidence

`web/src/lib/server/geography.integration.test.ts` compares the service response
to independent joins over the fact and dimensions. All five cases passed. The
following exact API values were captured after the passing reconciliation:

| Slice | Total records | Applications | Credit decisions | Originations | Denials | Origination rate | Denial rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Overall, all years | 12,006,526 | 10,471,829 | 8,189,970 | 5,710,620 | 2,123,781 | 69.7270% | 25.9315% |
| California, 2025 | 1,161,292 | 1,026,242 | 791,639 | 572,268 | 177,363 | 72.2890% | 22.4045% |
| Texas, 2024 | 1,074,771 | 911,271 | 710,206 | 494,656 | 184,473 | 69.6497% | 25.9746% |
| Los Angeles County, 2025 | 223,903 | 198,249 | 152,082 | 106,699 | 36,720 | 70.1589% | 24.1449% |
| LEI `549300FGXN1K3HLB1R50`, all years | 498,751 | 495,420 | 431,983 | 333,774 | 89,216 | 77.2655% | 20.6527% |

The county slice resolved FIPS `06037` to “Los Angeles County.”

## Tests and commands executed

```powershell
python -m compileall -q etl_hmda.py gen_dict.py load_data.py profile_script.py smoke_test_etl.py src scripts tests
python -m pytest -v --basetemp=.pytest-tmp
python load_data.py --validate-only

cd web
$env:RUN_DB_INTEGRATION_TESTS='true'; pnpm test src/lib/server/geography.integration.test.ts --reporter=verbose
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Actual results:

- Python compilation: passed.
- Existing Python tests: 43 passed in 7.87 seconds on the final rerun.
- Warehouse validation: all 13 checks passed over 12,006,526 staging and fact
  rows; all reported defect/reconciliation counts were zero.
- PostgreSQL geography reconciliation: 5 passed in 30.40 seconds on the final rerun.
- Frontend unit tests: 22 passed; 5 opt-in DB tests skipped in the unit-only run.
- ESLint: passed with no warnings.
- TypeScript: passed.
- Next.js production build: passed; `/geography` emitted as a static page with
  dynamic API routes and a 143 kB first-load bundle in the measured build.

## Browser verification and UX observations

The production build was inspected in the in-app Chromium browser at desktop and
390×844 mobile sizes, in both light and dark themes.

- Desktop: the map and selected-market panel read as one coordinated workspace;
  the national view showed five enabled data states and the rest as muted context.
- Drill-down: selecting California changed the URL to `?state=CA`, zoomed to the
  county map, exposed official county names, and updated all surrounding context.
- County: selecting Los Angeles changed the URL to `?state=CA&county=06037`, added
  the full breadcrumb, persisted a map outline, and showed county-vs-state facts.
- Metric switch: denial rate persisted as `metric=denialRate`, recolored and
  reranked the view, and updated the selected county’s deterministic rank.
- URL restoration: a full reload restored California → Los Angeles County,
  denial-rate mode, KPIs, observations, and the selected geography.
- Mobile: the sidebar becomes a labeled navigation drawer; the filters and
  three-option metric control reflow above a large 300px touch map; context stacks
  below rather than shrinking the map; the comparison table remains horizontally
  scrollable.
- Invalid filter: the injection-like state URL rendered the polished API error
  state with retry/reset and the API returned 400.
- Empty data: a syntactically valid cross-state county selection rendered the
  explicit empty state without converting missing observations to zero.
- Loading: the route presented skeletons with an appropriate geographic loading
  label.
- Console: no warning or error entries were present after the full interaction
  sequence.

The desktop/light, desktop/dark, California county-map, mobile/dark, invalid, and
empty-state screenshots were visually inspected during browser verification.

## Performance observations

- Materialized-view build plus indexing took 76.066 seconds on the local
  12,006,526-row warehouse.
- First captured cold national API response: 3,987 ms.
- Subsequent warmed national responses before the redundant-query cleanup:
  574–569 ms.
- Captured filtered responses: California 2025 244 ms; Texas 2024 287 ms; Los
  Angeles County 2025 200 ms; lender slice 140 ms.
- Responses are bounded to five state rows or the selected state’s county set;
  no source-level HMDA rows are sent to the browser.

The national cold path is acceptable for the first additive pass but remains the
main performance candidate for Phase 2A follow-up monitoring. A redundant parent
aggregate was removed after measurement; server caching headers allow a five-
minute shared cache with stale revalidation.

## Files changed

- SQL/data: `sql/10_create_phase2_geography.sql`, generated county seed, county
  seed generator, local TopoJSON boundary asset.
- API/server: geography and lender routes, geographic service, query/filter
  contracts, observations, and integration tests.
- UI: Geographic Explorer page/components, navigation activation, responsive
  map/search/context/table states, and reusable state-label improvements.
- Configuration/docs: dependencies and lockfile, `.gitignore`, README, design
  audit, and this report.

The repository’s generic Python `lib/` ignore pattern also matched
`web/src/lib/`, so the canonical Phase 1 analytics/server sources were present
locally but absent from the Phase 1 checkpoint. The rule is now anchored to the
repository root (`/lib/`), allowing the existing web library plus the Phase 2A
additions to be versioned. Phase 1 library behavior was not redesigned.

## New dependencies and rationale

- `topojson-client`: converts the compact local TopoJSON geometry to SVG-ready
  GeoJSON features.
- `d3-geo`: produces deterministic SVG paths and state-focused bounds without a
  map runtime.
- `us-atlas` (development only): provides the reviewed Census-derived,
  preprojected boundary source copied into `public/geo`.
- `@types/d3-geo`, `@types/topojson-client`, `@types/geojson`, and
  `@types/topojson-specification` (development only): preserve strict TypeScript
  coverage for the geometry pipeline.

MapLibre, deck.gl, and a slippy-map stack were not added.

## Remaining limitations and next milestone

- Only the five warehouse states carry analytical values; other states are map
  context and are intentionally not selectable.
- The reference correctly exposes a small number of cross-state/malformed FIPS
  values already present in the warehouse rather than repairing source data.
- The boundary geometry is Census 2017 while county names use Census 2025. No
  relevant county-equivalent boundary mismatch was observed for the five-state
  scope, but this vintage difference is documented.
- The ranked table renders the complete selected-state comparison; future scale
  expansion may justify pagination or virtualization.
- No standalone multi-state comparison mode was added because the national map
  and table already provide the smallest useful state comparison.

The next safe milestone is to agree on the Phase 2B longitudinal interaction
model before implementing Multi-Year Trends. It should reuse the same governed
counts and server-side rate recomputation rather than duplicate definitions.
