"use client";

import { RotateCcw, SlidersHorizontal } from "lucide-react";

import type { ExecutiveData, ExecutiveFilters } from "@/lib/analytics/types";

interface FilterBarProps {
  filters: ExecutiveFilters;
  options: ExecutiveData["options"];
  loading: boolean;
  onChange: (next: ExecutiveFilters) => void;
  onReset: () => void;
}

const selectClass =
  "h-10 min-w-0 rounded-xl border border-slate-200 bg-white px-3 pr-8 text-sm font-medium text-slate-800 shadow-sm outline-none hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-slate-600";

export function FilterBar({ filters, options, loading, onChange, onReset }: FilterBarProps) {
  return (
    <section aria-label="Global analytics filters" className="rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_1px_2px_rgba(15,23,42,0.02)] dark:border-slate-800 dark:bg-slate-900 sm:p-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-white">
          <span className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <SlidersHorizontal size={17} aria-hidden="true" />
          </span>
          Global view
          {loading ? <span className="ml-1 size-1.5 animate-pulse rounded-full bg-blue-500" aria-label="Refreshing analytics" /> : null}
        </div>

        <div className="grid gap-3 sm:grid-cols-[repeat(3,minmax(0,1fr))_auto] xl:min-w-[720px]">
          <label className="grid gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
            Year
            <select value={filters.year ?? "all"} className={selectClass} onChange={(event) => onChange({ ...filters, year: event.target.value === "all" ? null : Number(event.target.value) })}>
              <option value="all">All years</option>
              {options.years.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
            State
            <select value={filters.state ?? "all"} className={selectClass} onChange={(event) => onChange({ ...filters, state: event.target.value === "all" ? null : event.target.value })}>
              <option value="all">All states</option>
              {options.states.map((state) => <option key={state.value} value={state.value}>{state.label}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">
            Loan purpose
            <select value={filters.loanPurpose ?? "all"} className={selectClass} onChange={(event) => onChange({ ...filters, loanPurpose: event.target.value === "all" ? null : event.target.value })}>
              <option value="all">All purposes</option>
              {options.loanPurposes.map((purpose) => <option key={purpose.value} value={purpose.value}>{purpose.label}</option>)}
            </select>
          </label>
          <button type="button" onClick={onReset} disabled={filters.year === null && filters.state === null && filters.loanPurpose === null} className="mt-auto inline-flex h-10 items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-semibold text-slate-500 hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-400 dark:hover:text-white">
            <RotateCcw size={15} aria-hidden="true" /> Reset
          </button>
        </div>
      </div>
    </section>
  );
}
