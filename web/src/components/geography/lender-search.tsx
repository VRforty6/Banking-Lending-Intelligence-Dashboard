"use client";

import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";

interface LenderOption { lei: string; label: string; applicationVolume: number }

export function LenderSearch({ selected, onSelect }: {
  selected: { lei: string; label: string } | null;
  onSelect: (lei: string | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<LenderOption[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      fetch(`/api/analytics/lenders?q=${encodeURIComponent(query)}`, { signal: controller.signal })
        .then((response) => response.ok ? response.json() as Promise<{ lenders: LenderOption[] }> : Promise.reject())
        .then((body) => setOptions(body.lenders))
        .catch(() => { if (!controller.signal.aborted) setOptions([]); });
    }, 180);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [open, query]);

  if (selected) {
    return <button type="button" onClick={() => onSelect(null)} className="inline-flex min-w-0 items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-left text-xs font-semibold text-blue-700 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-300"><span className="truncate">{selected.label}</span><X size={14} aria-hidden="true" /></button>;
  }

  return (
    <div className="relative min-w-[220px] flex-1 sm:max-w-sm">
      <Search size={15} aria-hidden="true" className="pointer-events-none absolute left-3 top-3 text-slate-400" />
      <input value={query} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 120)} placeholder="Search lender name or LEI" aria-label="Search lenders" className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/15 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100" />
      {open ? <div className="absolute left-0 right-0 top-12 z-30 max-h-72 overflow-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl dark:border-slate-700 dark:bg-slate-900">{options.length ? options.map((option) => <button key={option.lei} type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => { onSelect(option.lei); setOpen(false); setQuery(""); }} className="block w-full rounded-lg px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800"><span className="block truncate text-xs font-semibold text-slate-800 dark:text-slate-100">{option.label}</span><span className="mt-0.5 block font-mono text-[10px] text-slate-400">{option.lei}</span></button>) : <p className="px-3 py-4 text-center text-xs text-slate-400">No matching lenders</p>}</div> : null}
    </div>
  );
}
