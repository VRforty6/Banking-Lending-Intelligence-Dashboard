import { Info } from "lucide-react";

export function ChartCard({
  title,
  description,
  children,
  detail,
  className = "",
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  detail?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`chart-card rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.02)] dark:border-slate-800 dark:bg-slate-900 ${className}`}>
      <header className="flex items-start justify-between gap-4 px-5 pb-2 pt-5 sm:px-6">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-slate-950 dark:text-white">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{description}</p>
        </div>
        <Info size={16} className="mt-0.5 shrink-0 text-slate-300 dark:text-slate-600" aria-hidden="true" />
      </header>
      <div className="px-2 pb-2 sm:px-3">{children}</div>
      {detail ? (
        <details className="border-t border-slate-100 px-5 py-3 text-xs dark:border-slate-800 sm:px-6">
          <summary className="cursor-pointer font-medium text-slate-500 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:text-slate-400 dark:hover:text-white">View accessible data table</summary>
          <div className="mt-3 overflow-x-auto">{detail}</div>
        </details>
      ) : null}
    </section>
  );
}
