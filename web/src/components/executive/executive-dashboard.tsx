"use client";

import type { EChartsCoreOption } from "echarts";
import {
  BadgeDollarSign,
  Banknote,
  CheckCircle2,
  FileStack,
  Landmark,
  ShieldX,
  Sparkles,
} from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EChart } from "@/components/charts/echart";
import { ChartCard } from "@/components/charts/chart-card";
import { filtersToQuery } from "@/lib/analytics/filters";
import type { ExecutiveData, ExecutiveFilters } from "@/lib/analytics/types";

import { DashboardError, DashboardSkeleton, EmptyDashboard } from "./dashboard-states";
import { FilterBar } from "./filter-bar";
import {
  formatCompact,
  formatMetric,
  formatNumber,
  formatPercent,
} from "./format";
import { MetricCard } from "./metric-card";

const chartColors = {
  blue: "#2563eb",
  teal: "#0f8f83",
  amber: "#d78b09",
  coral: "#d55a52",
  violet: "#7c6ee6",
  slate: "#64748b",
  grid: "rgba(148, 163, 184, 0.18)",
};

const tableClass = "w-full border-collapse text-left text-xs";
const headerCellClass = "border-b border-slate-200 px-2 py-2 font-semibold text-slate-500 dark:border-slate-700 dark:text-slate-400";
const cellClass = "border-b border-slate-100 px-2 py-2 text-slate-700 dark:border-slate-800 dark:text-slate-200";

interface ChartClick {
  name?: string | number;
  data?: { code?: string; year?: number } | number | number[];
}

function clickCode(point: ChartClick): string | undefined {
  return point.data && !Array.isArray(point.data) && typeof point.data === "object"
    ? point.data.code
    : undefined;
}

function parseFilters(searchParams: URLSearchParams): ExecutiveFilters {
  const yearValue = searchParams.get("year");
  const stateValue = searchParams.get("state");
  const purposeValue = searchParams.get("purpose");
  return {
    year: yearValue && /^\d{4}$/.test(yearValue) ? Number(yearValue) : null,
    state: stateValue ? stateValue.toUpperCase() : null,
    loanPurpose: purposeValue || null,
  };
}

function tooltipBox(lines: string[]) {
  return `<div style="min-width:150px;padding:2px 1px"><div style="font-weight:650;margin-bottom:7px">${lines[0]}</div>${lines.slice(1).map((line) => `<div style="display:flex;justify-content:space-between;gap:20px;margin-top:4px">${line}</div>`).join("")}</div>`;
}

function RankedList({
  title,
  description,
  rows,
}: {
  title: string;
  description: string;
  rows: Array<{ key: string; label: string; value: number; meta?: string }>;
}) {
  const maximum = rows[0]?.value ?? 1;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.02)] dark:border-slate-800 dark:bg-slate-900 sm:p-6">
      <h2 className="text-[15px] font-semibold tracking-tight text-slate-950 dark:text-white">{title}</h2>
      <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{description}</p>
      <ol className="mt-5 space-y-4">
        {rows.map((row, index) => (
          <li key={row.key} className="grid grid-cols-[24px_minmax(0,1fr)_auto] items-center gap-3">
            <span className="font-mono text-[11px] font-semibold text-slate-400">{String(index + 1).padStart(2, "0")}</span>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium text-slate-800 dark:text-slate-100" title={row.label}>{row.label}</span>
                {row.meta ? <span className="hidden shrink-0 font-mono text-[10px] text-slate-400 2xl:inline">{row.meta}</span> : null}
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.max(3, (row.value / maximum) * 100)}%` }} />
              </div>
            </div>
            <span className="metric-value text-sm font-semibold text-slate-900 dark:text-white">{formatCompact(row.value)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function ExecutiveDashboard() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);
  const [data, setData] = useState<ExecutiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const query = searchParams.toString();

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetch(`/api/analytics/executive${query ? `?${query}` : ""}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        const body = (await response.json()) as ExecutiveData | { error?: string; details?: string[] | string };
        if (!response.ok) {
          const detail =
            "details" in body && Array.isArray(body.details)
              ? body.details.join(". ")
              : "details" in body && typeof body.details === "string"
                ? body.details
                : undefined;
          throw new Error(detail || ("error" in body ? body.error : undefined) || "The analytics request failed.");
        }
        return body as ExecutiveData;
      })
      .then(setData)
      .catch((requestError: unknown) => {
        if (requestError instanceof DOMException && requestError.name === "AbortError") return;
        setError(requestError instanceof Error ? requestError.message : "The analytics request failed.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [query, requestVersion]);

  const updateFilters = useCallback(
    (next: ExecutiveFilters) => {
      const nextQuery = filtersToQuery(next);
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  const resetFilters = useCallback(() => updateFilters({ year: null, state: null, loanPurpose: null }), [updateFilters]);

  const trendOption = useMemo<EChartsCoreOption>(() => ({
    animationDuration: 360,
    aria: { enabled: true, decal: { show: true } },
    color: [chartColors.blue, chartColors.teal, chartColors.coral],
    grid: { left: 54, right: 50, top: 50, bottom: 42 },
    legend: { top: 8, itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(15, 23, 42, 0.96)",
      borderWidth: 0,
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: unknown) => {
        const points = params as Array<{ axisValue: number; seriesName: string; value: number }>;
        if (!points.length) return "";
        return tooltipBox([
          String(points[0].axisValue),
          ...points.map((point) => `<span>${point.seriesName}</span><strong>${point.seriesName === "Applications" ? formatNumber(point.value) : formatPercent(point.value)}</strong>`),
        ]);
      },
    },
    xAxis: { type: "category", data: data?.trend.map((row) => row.year) ?? [], axisTick: { show: false }, axisLine: { lineStyle: { color: chartColors.grid } } },
    yAxis: [
      { type: "value", splitLine: { lineStyle: { color: chartColors.grid } }, axisLabel: { formatter: (value: number) => formatCompact(value) } },
      { type: "value", min: 0, max: 1, splitLine: { show: false }, axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%` } },
    ],
    series: [
      { name: "Applications", type: "bar", barMaxWidth: 48, itemStyle: { borderRadius: [6, 6, 0, 0] }, data: data?.trend.map((row) => ({ value: row.applicationVolume, year: row.year })) ?? [] },
      { name: "Origination rate", type: "line", yAxisIndex: 1, symbolSize: 8, lineStyle: { width: 2.5 }, data: data?.trend.map((row) => row.originationRate) ?? [] },
      { name: "Denial rate", type: "line", yAxisIndex: 1, symbol: "emptyCircle", symbolSize: 8, lineStyle: { width: 2.5 }, data: data?.trend.map((row) => row.denialRate) ?? [] },
    ],
  }), [data?.trend]);

  const outcomeOption = useMemo<EChartsCoreOption>(() => ({
    animationDuration: 360,
    aria: { enabled: true, decal: { show: true } },
    color: [chartColors.blue],
    grid: { left: 178, right: 28, top: 16, bottom: 28 },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.96)",
      borderWidth: 0,
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: unknown) => {
        const point = params as { name: string; value: number; data: { code: number } };
        const total = data?.context.totalHmdaRecords ?? 0;
        return tooltipBox([point.name, `<span>HMDA records</span><strong>${formatNumber(point.value)}</strong>`, `<span>Share of all records</span><strong>${total ? formatPercent(point.value / total) : "—"}</strong>`, `<span>Action code</span><strong>${point.data.code}</strong>`]);
      },
    },
    xAxis: { type: "value", splitLine: { lineStyle: { color: chartColors.grid } }, axisLabel: { formatter: (value: number) => formatCompact(value) } },
    yAxis: { type: "category", inverse: true, data: data?.outcomes.map((row) => row.label) ?? [], axisTick: { show: false }, axisLine: { show: false }, axisLabel: { width: 160, overflow: "truncate" } },
    series: [{ type: "bar", barWidth: 15, itemStyle: { borderRadius: [0, 5, 5, 0], color: (params: { dataIndex: number }) => [chartColors.teal, chartColors.violet, chartColors.coral, chartColors.amber, chartColors.slate, "#94a3b8", "#b7791f", "#a78bfa"][params.dataIndex] }, data: data?.outcomes.map((row) => ({ value: row.value, code: row.code })) ?? [] }],
  }), [data?.context.totalHmdaRecords, data?.outcomes]);

  const purposeOption = useMemo<EChartsCoreOption>(() => ({
    animationDuration: 360,
    aria: { enabled: true, decal: { show: true } },
    grid: { left: 142, right: 42, top: 16, bottom: 34 },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.96)", borderWidth: 0, textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: unknown) => {
        const point = params as { name: string; value: number; data: { code: string } };
        const total = data?.kpis.applicationVolume.value ?? 0;
        return tooltipBox([point.name, `<span>Applications</span><strong>${formatNumber(point.value)}</strong>`, `<span>Share of volume</span><strong>${total ? formatPercent(point.value / total) : "—"}</strong>`, `<span>Purpose code</span><strong>${point.data.code}</strong>`]);
      },
    },
    xAxis: { type: "value", splitLine: { lineStyle: { color: chartColors.grid } }, axisLabel: { formatter: (value: number) => formatCompact(value) } },
    yAxis: { type: "category", inverse: true, data: data?.loanPurposes.map((row) => row.label) ?? [], axisTick: { show: false }, axisLine: { show: false }, axisLabel: { width: 130, overflow: "truncate" } },
    series: [{ type: "bar", barWidth: 17, itemStyle: { color: chartColors.blue, borderRadius: [0, 5, 5, 0] }, data: data?.loanPurposes.map((row) => ({ value: row.value, code: row.code })) ?? [] }],
  }), [data?.kpis.applicationVolume.value, data?.loanPurposes]);

  const stateOption = useMemo<EChartsCoreOption>(() => ({
    animationDuration: 360,
    aria: { enabled: true, decal: { show: true } },
    color: [chartColors.teal, chartColors.coral],
    grid: { left: 92, right: 32, top: 48, bottom: 34 },
    legend: { top: 8, itemWidth: 10, itemHeight: 10, textStyle: { fontSize: 11 } },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(15, 23, 42, 0.96)", borderWidth: 0, textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: unknown) => {
        const points = params as Array<{ axisValue: string; seriesName: string; value: number; dataIndex: number }>;
        if (!points.length) return "";
        const state = data?.states[points[0].dataIndex];
        return tooltipBox([points[0].axisValue, ...points.map((point) => `<span>${point.seriesName}</span><strong>${formatPercent(point.value)}</strong>`), `<span>Applications</span><strong>${state ? formatNumber(state.applicationVolume) : "—"}</strong>`]);
      },
    },
    xAxis: { type: "value", min: 0, max: 1, splitLine: { lineStyle: { color: chartColors.grid } }, axisLabel: { formatter: (value: number) => `${Math.round(value * 100)}%` } },
    yAxis: { type: "category", inverse: true, data: data?.states.map((row) => row.label) ?? [], axisTick: { show: false }, axisLine: { show: false } },
    series: [
      { name: "Origination rate", type: "bar", barMaxWidth: 15, itemStyle: { borderRadius: [0, 4, 4, 0] }, data: data?.states.map((row) => ({ value: row.originationRate, code: row.code })) ?? [] },
      { name: "Denial rate", type: "bar", barMaxWidth: 15, itemStyle: { borderRadius: [0, 4, 4, 0] }, data: data?.states.map((row) => ({ value: row.denialRate, code: row.code })) ?? [] },
    ],
  }), [data?.states]);

  if (!data && loading) {
    return <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><DashboardSkeleton /></main>;
  }

  if (!data || error) {
    return <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8"><DashboardError message={error ?? "No analytics response was returned."} onRetry={() => setRequestVersion((version) => version + 1)} onReset={resetFilters} /></main>;
  }

  const applicationVolume = data.kpis.applicationVolume.value ?? 0;
  const refreshedAt = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(data.context.refreshedAt));

  return (
    <main className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-blue-600 dark:text-blue-400"><Sparkles size={14} aria-hidden="true" /> Decision intelligence</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-[-0.035em] text-slate-950 dark:text-white sm:text-4xl">Lending performance, clearly framed.</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">A concise view of application demand, completed decisions, borrower context, and market concentration from the validated HMDA warehouse.</p>
        </div>
        <p className="text-xs font-medium text-slate-400">Aggregate refreshed {refreshedAt}</p>
      </header>

      <FilterBar filters={data.filters} options={data.options} loading={loading} onChange={updateFilters} onReset={resetFilters} />

      {!data.hasData ? <div className="mt-5"><EmptyDashboard onReset={resetFilters} /></div> : (
        <>
          <section aria-label="Executive key performance indicators" className={`mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-5 ${loading ? "opacity-65" : "opacity-100"}`}>
            <MetricCard label="Application volume" value={formatMetric(data.kpis.applicationVolume.value, "number")} detail="Action codes 1–5, 7 and 8; purchased loans excluded" icon={FileStack} tone="blue" />
            <MetricCard label="Origination rate" value={formatMetric(data.kpis.originationRate.value, "percent")} detail={`${formatNumber(data.kpis.originationRate.numerator ?? 0)} of ${formatNumber(data.kpis.originationRate.denominator ?? 0)} credit decisions`} icon={CheckCircle2} tone="teal" />
            <MetricCard label="Denial rate" value={formatMetric(data.kpis.denialRate.value, "percent")} detail={`${formatNumber(data.kpis.denialRate.numerator ?? 0)} of ${formatNumber(data.kpis.denialRate.denominator ?? 0)} credit decisions`} icon={ShieldX} tone="amber" />
            <MetricCard label="Avg originated loan" value={formatMetric(data.kpis.averageOriginatedLoanAmount.value, "currency")} detail="Average loan amount for action code 1 only" icon={Banknote} tone="slate" />
            <MetricCard label="Median applicant income" value={formatMetric(data.kpis.medianApplicantIncome.value, "income")} detail="HMDA income is reported in thousands of dollars" icon={BadgeDollarSign} tone="slate" />
          </section>

          <section aria-label="Population context" className="mt-4 grid gap-px overflow-hidden rounded-2xl border border-slate-200 bg-slate-200 dark:border-slate-800 dark:bg-slate-800 sm:grid-cols-3">
            {[
              ["Total HMDA records", formatNumber(data.context.totalHmdaRecords), "All valid action codes 1–8"],
              ["Credit decisions", formatNumber(data.context.creditDecisions), "Decision denominator: codes 1–3"],
              ["Purchased loans", formatNumber(data.context.purchasedLoans), "Shown in outcomes, excluded from volume"],
            ].map(([label, value, detail]) => (
              <div key={label} className="bg-white px-5 py-4 dark:bg-slate-900">
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">{label}</p>
                <div className="mt-1.5 flex items-baseline gap-3"><span className="metric-value text-lg font-semibold text-slate-950 dark:text-white">{value}</span><span className="text-xs text-slate-500 dark:text-slate-400">{detail}</span></div>
              </div>
            ))}
          </section>

          <section className={`mt-5 grid gap-4 xl:grid-cols-2 ${loading ? "opacity-65" : "opacity-100"}`}>
            <ChartCard title="Volume and decision rates" description="Select a year to focus the global view. Rates retain the completed-decision denominator." detail={
              <table className={tableClass}><thead><tr><th className={headerCellClass}>Year</th><th className={headerCellClass}>Applications</th><th className={headerCellClass}>Origination rate</th><th className={headerCellClass}>Denial rate</th></tr></thead><tbody>{data.trend.map((row) => <tr key={row.year}><td className={cellClass}>{row.year}</td><td className={cellClass}>{formatNumber(row.applicationVolume)}</td><td className={cellClass}>{row.originationRate === null ? "—" : formatPercent(row.originationRate)}</td><td className={cellClass}>{row.denialRate === null ? "—" : formatPercent(row.denialRate)}</td></tr>)}</tbody></table>
            }>
              <EChart option={trendOption} className="h-[330px]" ariaLabel="Application volume bars with origination and denial rate lines by year" onEvents={{ click: (raw) => { const point = raw as ChartClick; const selectedYear = Number(point.name); if (Number.isInteger(selectedYear)) updateFilters({ ...filters, year: selectedYear }); } }} />
            </ChartCard>

            <ChartCard title="Reported HMDA outcomes" description="All valid HMDA records are retained here, including purchased loans and preapproval outcomes." detail={
              <table className={tableClass}><thead><tr><th className={headerCellClass}>Code</th><th className={headerCellClass}>Outcome</th><th className={headerCellClass}>Records</th></tr></thead><tbody>{data.outcomes.map((row) => <tr key={row.code}><td className={cellClass}>{row.code}</td><td className={cellClass}>{row.label}</td><td className={cellClass}>{formatNumber(row.value)}</td></tr>)}</tbody></table>
            }>
              <EChart option={outcomeOption} className="h-[330px]" ariaLabel="Horizontal bars showing record counts for HMDA action codes one through eight" />
            </ChartCard>

            <ChartCard title="Application mix by loan purpose" description="Select a bar to filter the dashboard to one loan purpose." detail={
              <table className={tableClass}><thead><tr><th className={headerCellClass}>Purpose</th><th className={headerCellClass}>Applications</th><th className={headerCellClass}>Share</th></tr></thead><tbody>{data.loanPurposes.map((row) => <tr key={row.code}><td className={cellClass}>{row.label}</td><td className={cellClass}>{formatNumber(row.value)}</td><td className={cellClass}>{applicationVolume ? formatPercent(row.value / applicationVolume) : "—"}</td></tr>)}</tbody></table>
            }>
              <EChart option={purposeOption} className="h-[320px]" ariaLabel="Horizontal bars comparing application volume by loan purpose" onEvents={{ click: (raw) => { const code = clickCode(raw as ChartClick); if (code) updateFilters({ ...filters, loanPurpose: code }); } }} />
            </ChartCard>

            <ChartCard title="Decision profile by state" description="Rates compare completed credit decisions. Select a state to focus the dashboard." detail={
              <table className={tableClass}><thead><tr><th className={headerCellClass}>State</th><th className={headerCellClass}>Applications</th><th className={headerCellClass}>Origination</th><th className={headerCellClass}>Denial</th></tr></thead><tbody>{data.states.map((row) => <tr key={row.code}><td className={cellClass}>{row.label}</td><td className={cellClass}>{formatNumber(row.applicationVolume)}</td><td className={cellClass}>{row.originationRate === null ? "—" : formatPercent(row.originationRate)}</td><td className={cellClass}>{row.denialRate === null ? "—" : formatPercent(row.denialRate)}</td></tr>)}</tbody></table>
            }>
              <EChart option={stateOption} className="h-[320px]" ariaLabel="Grouped horizontal bars comparing origination and denial rates by state" onEvents={{ click: (raw) => { const code = clickCode(raw as ChartClick); if (code) updateFilters({ ...filters, state: code }); } }} />
            </ChartCard>
          </section>

          <section className={`mt-4 grid gap-4 xl:grid-cols-2 ${loading ? "opacity-65" : "opacity-100"}`}>
            <RankedList title="Leading lenders by application volume" description="Ranked at unique LEI grain; official names fall back to LEI when unavailable." rows={data.topLenders.map((row) => ({ key: row.lei, label: row.label, value: row.applicationVolume, meta: row.lei.slice(-6) }))} />
            <RankedList title="Highest-volume counties" description="County labels use the existing state and five-digit FIPS reporting grain." rows={data.topCounties.map((row) => ({ key: `${row.state}-${row.county}`, label: row.label, value: row.applicationVolume }))} />
          </section>

          <details className="mt-4 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
            <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:text-white"><Landmark size={16} className="text-blue-500" aria-hidden="true" /> Metric definitions and population rules</summary>
            <dl className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{data.definitions.map((definition) => <div key={definition.name} className="rounded-xl bg-slate-50 p-4 dark:bg-slate-800/70"><dt className="text-xs font-semibold text-slate-900 dark:text-white">{definition.name}</dt><dd className="mt-1.5 text-xs leading-5 text-slate-500 dark:text-slate-400">{definition.definition}</dd></div>)}</dl>
          </details>
        </>
      )}
    </main>
  );
}
