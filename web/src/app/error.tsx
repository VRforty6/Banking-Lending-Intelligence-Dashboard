"use client";

import { RotateCcw } from "lucide-react";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 p-6 dark:bg-slate-950">
      <section className="max-w-lg rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-600">Unable to load</p>
        <h1 className="mt-3 text-2xl font-semibold text-slate-950 dark:text-white">The analytics workspace hit an error</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">Try the request again. If it continues, confirm the PostgreSQL analytics views are available.</p>
        <button type="button" onClick={reset} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:bg-white dark:text-slate-950">
          <RotateCcw size={16} aria-hidden="true" /> Retry
        </button>
      </section>
    </main>
  );
}
