"use client";

import { AlertTriangle, DatabaseZap, RotateCcw } from "lucide-react";

export function DashboardSkeleton() {
  return (
    <div className="space-y-5" aria-label="Loading executive analytics" aria-busy="true">
      <div className="h-24 rounded-2xl skeleton-shimmer" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }, (_, index) => <div key={index} className="h-36 rounded-2xl skeleton-shimmer" />)}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="h-[420px] rounded-2xl skeleton-shimmer" />
        <div className="h-[420px] rounded-2xl skeleton-shimmer" />
      </div>
    </div>
  );
}

export function DashboardError({ message, onRetry, onReset }: { message: string; onRetry: () => void; onReset: () => void }) {
  return (
    <section className="grid min-h-[56vh] place-items-center rounded-3xl border border-dashed border-rose-200 bg-rose-50/40 p-8 text-center dark:border-rose-900/60 dark:bg-rose-950/10">
      <div className="max-w-lg">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-rose-100 text-rose-600 dark:bg-rose-950 dark:text-rose-300"><AlertTriangle size={22} aria-hidden="true" /></span>
        <h2 className="mt-5 text-xl font-semibold text-slate-950 dark:text-white">Analytics unavailable</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{message}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button type="button" onClick={onRetry} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-white dark:text-slate-950"><RotateCcw size={15} aria-hidden="true" /> Retry</button>
          <button type="button" onClick={onReset} className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:border-slate-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200">Reset filters</button>
        </div>
      </div>
    </section>
  );
}

export function EmptyDashboard({ onReset }: { onReset: () => void }) {
  return (
    <section className="grid min-h-[48vh] place-items-center rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
      <div className="max-w-md">
        <span className="mx-auto grid size-12 place-items-center rounded-2xl bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-300"><DatabaseZap size={22} aria-hidden="true" /></span>
        <h2 className="mt-5 text-xl font-semibold text-slate-950 dark:text-white">No records match this view</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">Try broadening the year, state, or loan-purpose filters. Missing observations are not converted to zero.</p>
        <button type="button" onClick={onReset} className="mt-6 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 dark:bg-white dark:text-slate-950">Clear filters</button>
      </div>
    </section>
  );
}
