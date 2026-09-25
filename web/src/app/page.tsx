import { AppShell } from "@/components/app-shell";
import { ExecutiveDashboard } from "@/components/executive/executive-dashboard";
import { Suspense } from "react";

export default function Home() {
  return (
    <AppShell>
      <Suspense fallback={<div className="min-h-[70vh] skeleton-shimmer" />}>
        <ExecutiveDashboard />
      </Suspense>
    </AppShell>
  );
}
