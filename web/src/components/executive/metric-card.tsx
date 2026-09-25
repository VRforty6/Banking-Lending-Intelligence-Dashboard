import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "blue",
}: {
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone?: "blue" | "teal" | "amber" | "slate";
}) {
  const tones = {
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-950/45 dark:text-blue-300",
    teal: "bg-teal-50 text-teal-600 dark:bg-teal-950/45 dark:text-teal-300",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-950/45 dark:text-amber-300",
    slate: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  };

  return (
    <article className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.02)] transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-[0_12px_32px_rgba(15,23,42,0.06)] dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.11em] text-slate-400">{label}</p>
        <span className={`grid size-9 shrink-0 place-items-center rounded-xl ${tones[tone]}`}>
          <Icon size={17} aria-hidden="true" />
        </span>
      </div>
      <p className="metric-value mt-5 text-[1.75rem] font-semibold leading-none text-slate-950 dark:text-white">{value}</p>
      <p className="mt-3 min-h-8 text-xs leading-4 text-slate-500 dark:text-slate-400">{detail}</p>
    </article>
  );
}
