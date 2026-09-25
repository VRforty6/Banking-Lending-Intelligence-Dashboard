import { Suspense } from "react";

import { AppShell } from "@/components/app-shell";
import { GeographicExplorer } from "@/components/geography/geographic-explorer";

export default function GeographyPage() {
  return <AppShell><Suspense fallback={<div className="min-h-[70vh] skeleton-shimmer" />}><GeographicExplorer /></Suspense></AppShell>;
}
