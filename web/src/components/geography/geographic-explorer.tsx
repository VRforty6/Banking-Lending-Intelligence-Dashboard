"use client";

import { ChevronRight, Compass, FileStack, Flag, RotateCcw, ShieldX, Sparkles } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { DashboardError, DashboardSkeleton, EmptyDashboard } from "@/components/executive/dashboard-states";
import { formatCompact, formatNumber, formatPercent } from "@/components/executive/format";
import { geographyFiltersToQuery, type GeographyData, type GeographyFilters, type GeographyMetric, type GeographyRow } from "@/lib/analytics/geography";

import { GeographyMap } from "./geography-map";
import { LenderSearch } from "./lender-search";

const metricOptions: Array<{ value: GeographyMetric; label: string }> = [
  { value: "applicationVolume", label: "Application volume" },
  { value: "originationRate", label: "Origination rate" },
  { value: "denialRate", label: "Denial rate" },
];
const defaultFilters: GeographyFilters = { year: null, state: null, county: null, lender: null, metric: "applicationVolume" };

const metricLabel = (metric: GeographyMetric) => metricOptions.find((option) => option.value === metric)?.label ?? metric;
const metricDisplay = (row: GeographyRow, metric: GeographyMetric) => metric === "applicationVolume" ? formatNumber(row.applicationVolume) : formatPercent(row[metric] ?? 0);

function ContextMetric({ label, value, detail, icon: Icon }: { label: string; value: string; detail: string; icon: typeof FileStack }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"><div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">{label}</p><Icon size={15} className="text-blue-500" aria-hidden="true" /></div><p className="metric-value mt-2 text-2xl font-semibold text-slate-950 dark:text-white">{value}</p><p className="mt-1 text-[11px] leading-4 text-slate-500 dark:text-slate-400">{detail}</p></div>;
}

export function GeographicExplorer() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const [data, setData] = useState<GeographyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(`/api/analytics/geography${query ? `?${query}` : ""}`, { signal: controller.signal, headers: { Accept: "application/json" } })
      .then(async (response) => {
        const body = await response.json() as GeographyData | { error?: string; details?: string[] };
        if (!response.ok) throw new Error("details" in body && body.details?.length ? body.details.join(". ") : "error" in body && body.error ? body.error : "The geography request failed.");
        return body as GeographyData;
      })
      .then(setData)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "The geography request failed.");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, requestVersion]);

  const filters = useMemo(() => data?.filters ?? defaultFilters, [data?.filters]);
  const updateFilters = useCallback((next: GeographyFilters) => {
    const nextQuery = geographyFiltersToQuery(next);
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
  }, [pathname, router]);
  const resetFilters = useCallback(() => updateFilters({ year: null, state: null, county: null, lender: null, metric: "applicationVolume" }), [updateFilters]);

  const stateFips = data?.scope.level === "national" ? null : data?.options.states.find((state) => state.value === filters.state)?.fips ?? null;
  const sortedRows = useMemo(() => data ? [...data.rows].sort((a, b) => (b[filters.metric] ?? -Infinity) - (a[filters.metric] ?? -Infinity)) : [], [data, filters.metric]);
  const selectGeography = useCallback((row: GeographyRow) => {
    if (row.level === "state") updateFilters({ ...filters, state: row.state, county: null });
    else updateFilters({ ...filters, county: row.code });
  }, [filters, updateFilters]);

  if (!data && loading) return <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><DashboardSkeleton label="Loading geographic analytics" /></main>;
  if (!data || error) return <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><DashboardError message={error ?? "No geography response was returned."} onRetry={() => setRequestVersion((value) => value + 1)} onReset={resetFilters} /></main>;

  const refreshedAt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(data.refreshedAt));

  return (
    <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-blue-600 dark:text-blue-400"><Compass size={14} aria-hidden="true" /> Coordinated market exploration</div><h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950 dark:text-white sm:text-4xl">Follow the lending geography.</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">Select a state, then a county. The map, decision context, ranked markets, and evidence-based observations move together.</p></div>
        <p className="text-xs font-medium text-slate-400">Aggregate refreshed {refreshedAt}</p>
      </header>

      <section aria-label="Geographic filters" className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-2">
          <select value={filters.year ?? "all"} onChange={(event) => updateFilters({ ...filters, year: event.target.value === "all" ? null : Number(event.target.value) })} aria-label="Reporting year" className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"><option value="all">All years</option>{data.options.years.map((year) => <option key={year}>{year}</option>)}</select>
          <LenderSearch selected={data.options.selectedLender} onSelect={(lender) => updateFilters({ ...filters, lender })} />
          <button type="button" onClick={resetFilters} className="inline-flex h-10 items-center gap-2 rounded-xl px-3 text-xs font-semibold text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><RotateCcw size={14} aria-hidden="true" /> Reset</button>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800" role="group" aria-label="Map metric">{metricOptions.map((option) => <button key={option.value} type="button" aria-pressed={filters.metric === option.value} onClick={() => updateFilters({ ...filters, metric: option.value })} className={`rounded-lg px-2 py-2 text-xs font-semibold leading-4 sm:px-3 ${filters.metric === option.value ? "bg-white text-blue-700 shadow-sm dark:bg-slate-950 dark:text-blue-300" : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white"}`}>{option.label}</button>)}</div>
      </section>

      {!data.hasData ? <div className="mt-5"><EmptyDashboard onReset={resetFilters} description="Try broadening the year, geography, or lender filters. Missing observations are not converted to zero." /></div> : <>
        <section className={`mt-5 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_12px_40px_rgba(15,23,42,0.05)] dark:border-slate-800 dark:bg-slate-900 ${loading ? "opacity-65" : "opacity-100"}`}>
          <div className="border-b border-slate-200 px-4 py-4 dark:border-slate-800 sm:px-6">
            <nav aria-label="Geography breadcrumb" className="flex flex-wrap items-center gap-1.5 text-xs font-semibold"><button type="button" onClick={() => updateFilters({ ...filters, state: null, county: null })} className={data.scope.level === "national" ? "text-slate-900 dark:text-white" : "text-blue-600 hover:underline dark:text-blue-400"}>United States</button>{filters.state ? <><ChevronRight size={13} className="text-slate-400" aria-hidden="true" /><button type="button" onClick={() => updateFilters({ ...filters, county: null })} className={filters.county ? "text-blue-600 hover:underline dark:text-blue-400" : "text-slate-900 dark:text-white"}>{data.parentScope?.level === "state" ? data.parentScope.name : data.scope.name}</button></> : null}{filters.county ? <><ChevronRight size={13} className="text-slate-400" aria-hidden="true" /><span className="text-slate-900 dark:text-white">{data.scope.name}</span></> : null}</nav>
            <div className="mt-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="text-xl font-semibold tracking-tight text-slate-950 dark:text-white">{data.scope.name}</h2><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Viewing {metricLabel(filters.metric)} · {filters.year ?? "all reporting years"}{data.options.selectedLender ? ` · ${data.options.selectedLender.label}` : " · all lenders"}</p></div><p className="text-[11px] text-slate-400">Select a {filters.state ? "county" : "state"} on the map or in the market table</p></div>
          </div>

          <div className="grid gap-0 xl:grid-cols-[minmax(0,1.65fr)_minmax(320px,0.75fr)]">
            <div className="p-3 sm:p-5"><GeographyMap rows={data.rows} stateFips={stateFips} selectedCode={filters.county} metric={filters.metric} onSelect={selectGeography} /></div>
            <aside className="border-t border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-950/25 xl:border-l xl:border-t-0 sm:p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Selected-market context</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                <ContextMetric label="Applications" value={formatCompact(data.metrics.applicationVolume)} detail="Action codes 1–5, 7 and 8" icon={FileStack} />
                <ContextMetric label="Credit decisions" value={formatCompact(data.metrics.creditDecisions)} detail="Action codes 1–3 denominator" icon={Flag} />
                <ContextMetric label="Originations" value={formatCompact(data.metrics.originations)} detail={data.metrics.originationRate === null ? "Rate unavailable" : `${formatPercent(data.metrics.originationRate)} of decisions`} icon={Sparkles} />
                <ContextMetric label="Denials" value={formatCompact(data.metrics.denials)} detail={data.metrics.denialRate === null ? "Rate unavailable" : `${formatPercent(data.metrics.denialRate)} of decisions`} icon={ShieldX} />
              </div>
              <div className="mt-5"><h3 className="text-sm font-semibold text-slate-950 dark:text-white">What stands out</h3><div className="mt-3 space-y-3">{data.observations.map((observation) => <div key={observation.id} className="border-l-2 border-blue-500 pl-3"><p className="text-xs font-semibold text-slate-800 dark:text-slate-100">{observation.label}</p><p className="mt-1 text-[11px] leading-5 text-slate-500 dark:text-slate-400">{observation.detail}</p></div>)}</div></div>
            </aside>
          </div>
        </section>

        <section className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 sm:p-6">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"><div><h2 className="text-[15px] font-semibold text-slate-950 dark:text-white">Ranked {filters.state ? "counties" : "states"}</h2><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Accessible equivalent to the choropleth, ranked by {metricLabel(filters.metric).toLowerCase()}.</p></div><span className="text-[11px] text-slate-400">{sortedRows.length} markets</span></div>
          <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[720px] border-collapse text-left text-xs"><thead><tr className="text-slate-400"><th className="border-b border-slate-200 px-2 py-2 dark:border-slate-700">Rank</th><th className="border-b border-slate-200 px-2 py-2 dark:border-slate-700">Market</th><th className="border-b border-slate-200 px-2 py-2 text-right dark:border-slate-700">{metricLabel(filters.metric)}</th><th className="border-b border-slate-200 px-2 py-2 text-right dark:border-slate-700">Applications</th><th className="border-b border-slate-200 px-2 py-2 text-right dark:border-slate-700">Credit decisions</th><th className="border-b border-slate-200 px-2 py-2 text-right dark:border-slate-700">Origination rate</th><th className="border-b border-slate-200 px-2 py-2 text-right dark:border-slate-700">Denial rate</th></tr></thead><tbody>{sortedRows.map((row, index) => <tr key={row.code} className="group cursor-pointer hover:bg-blue-50/60 dark:hover:bg-blue-950/20" onClick={() => selectGeography(row)}><td className="border-b border-slate-100 px-2 py-3 font-mono text-slate-400 dark:border-slate-800">{String(index + 1).padStart(2, "0")}</td><td className="border-b border-slate-100 px-2 py-3 dark:border-slate-800"><button type="button" onClick={(event) => { event.stopPropagation(); selectGeography(row); }} className="font-semibold text-slate-800 group-hover:text-blue-700 dark:text-slate-100 dark:group-hover:text-blue-300">{row.name}</button><span className="ml-2 font-mono text-[10px] text-slate-400">{row.code}</span></td><td className="metric-value border-b border-slate-100 px-2 py-3 text-right font-semibold text-blue-700 dark:border-slate-800 dark:text-blue-300">{metricDisplay(row, filters.metric)}</td><td className="border-b border-slate-100 px-2 py-3 text-right text-slate-600 dark:border-slate-800 dark:text-slate-300">{formatNumber(row.applicationVolume)}</td><td className="border-b border-slate-100 px-2 py-3 text-right text-slate-600 dark:border-slate-800 dark:text-slate-300">{formatNumber(row.creditDecisions)}</td><td className="border-b border-slate-100 px-2 py-3 text-right text-slate-600 dark:border-slate-800 dark:text-slate-300">{row.originationRate === null ? "—" : formatPercent(row.originationRate)}</td><td className="border-b border-slate-100 px-2 py-3 text-right text-slate-600 dark:border-slate-800 dark:text-slate-300">{row.denialRate === null ? "—" : formatPercent(row.denialRate)}</td></tr>)}</tbody></table></div>
        </section>
      </>}
    </main>
  );
}
