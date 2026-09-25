"use client";

import {
  BarChart3,
  Blocks,
  Building2,
  ChevronRight,
  CircleGauge,
  Landmark,
  Map,
  Menu,
  ShieldCheck,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";

import { ThemeToggle } from "./theme-toggle";

const navigation: ReadonlyArray<{
  label: string;
  icon: LucideIcon;
  active?: boolean;
  phase?: number;
}> = [
  { label: "Executive Overview", icon: CircleGauge, active: true },
  { label: "Geographic Explorer", icon: Map, phase: 2 },
  { label: "Approval & Denial", icon: ShieldCheck, phase: 4 },
  { label: "Multi-Year Trends", icon: TrendingUp, phase: 2 },
  { label: "Lender Explorer", icon: Building2, phase: 3 },
  { label: "Borrower Segmentation", icon: Users, phase: 4 },
  { label: "Data Quality / Architecture", icon: Blocks, phase: 5 },
];

function NavigationContent() {
  return (
    <>
      <div className="flex h-20 items-center gap-3 px-5">
        <div className="grid size-10 place-items-center rounded-xl bg-blue-600 text-white shadow-[0_8px_24px_rgba(37,99,235,0.28)]">
          <Landmark size={20} aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-white">HMDA Intelligence</p>
          <p className="mt-0.5 text-[11px] font-medium uppercase tracking-[0.14em] text-slate-400">Lending analytics</p>
        </div>
      </div>

      <nav aria-label="Analytics sections" className="mt-3 flex-1 space-y-1 px-3">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              type="button"
              disabled={!item.active}
              aria-current={item.active ? "page" : undefined}
              title={!item.active ? `Planned for Phase ${item.phase}` : undefined}
              className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium ${item.active ? "bg-white/10 text-white" : "cursor-not-allowed text-slate-500"}`}
            >
              <Icon size={17} aria-hidden="true" className={item.active ? "text-blue-300" : "text-slate-600"} />
              <span className="flex-1 truncate">{item.label}</span>
              {item.active ? <ChevronRight size={14} aria-hidden="true" className="text-slate-500" /> : <span className="text-[10px] uppercase tracking-wider">P{item.phase}</span>}
            </button>
          );
        })}
      </nav>

      <div className="m-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
        <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-slate-300">
          <BarChart3 size={15} className="text-blue-300" aria-hidden="true" /> Trusted warehouse
        </div>
        <p className="text-xs leading-5 text-slate-500">12.0M validated records across five states and three reporting years.</p>
      </div>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[252px] flex-col bg-[#0b1628] lg:flex">
        <NavigationContent />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-[286px] flex-col bg-[#0b1628] shadow-2xl">
            <button type="button" onClick={() => setMobileOpen(false)} className="absolute right-3 top-5 grid size-9 place-items-center rounded-xl text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Close navigation">
              <X size={19} aria-hidden="true" />
            </button>
            <NavigationContent />
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-[252px]">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/88 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button type="button" onClick={() => setMobileOpen(true)} className="grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm lg:hidden dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200" aria-label="Open navigation">
              <Menu size={18} aria-hidden="true" />
            </button>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-slate-400">Analytics workspace</p>
              <p className="text-sm font-semibold text-slate-900 dark:text-white">Executive Overview</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 sm:inline-flex dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300">
              <span className="size-1.5 rounded-full bg-emerald-500" aria-hidden="true" /> PostgreSQL source
            </span>
            <ThemeToggle />
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
