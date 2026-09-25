"use client";

import { geoPath } from "d3-geo";
import { feature } from "topojson-client";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import type { GeometryCollection, Topology } from "topojson-specification";
import { useEffect, useMemo, useState } from "react";

import { formatNumber, formatPercent } from "@/components/executive/format";
import type { GeographyMetric, GeographyRow } from "@/lib/analytics/geography";
import { metricValue } from "@/lib/analytics/geography";

type Atlas = Topology<{ states: GeometryCollection; counties: GeometryCollection }>;

const metricLabels: Record<GeographyMetric, string> = {
  applicationVolume: "Application volume",
  originationRate: "Origination rate",
  denialRate: "Denial rate",
};

function fillFor(value: number | null, values: number[], metric: GeographyMetric) {
  if (value === null || !values.length) return "#cbd5e1";
  const sorted = [...values].sort((a, b) => a - b);
  const rank = sorted.findIndex((candidate) => candidate >= value);
  const bucket = Math.min(4, Math.floor(((rank < 0 ? sorted.length - 1 : rank) / Math.max(1, sorted.length - 1)) * 5));
  const palettes = metric === "denialRate"
    ? ["#fff7ed", "#fed7aa", "#fdba74", "#f97316", "#c2410c"]
    : ["#eff6ff", "#bfdbfe", "#93c5fd", "#3b82f6", "#1d4ed8"];
  return palettes[bucket];
}

function geometryId(featureItem: Feature) {
  return String(featureItem.id ?? "").padStart(featureItem.id && String(featureItem.id).length <= 2 ? 2 : 5, "0");
}

export function GeographyMap({ rows, stateFips, selectedCode, metric, onSelect }: {
  rows: GeographyRow[];
  stateFips: string | null;
  selectedCode: string | null;
  metric: GeographyMetric;
  onSelect: (row: GeographyRow) => void;
}) {
  const [atlas, setAtlas] = useState<Atlas | null>(null);
  const [error, setError] = useState(false);
  const [activeCode, setActiveCode] = useState<string | null>(null);

  useEffect(() => {
    fetch("/geo/counties-albers-10m.json")
      .then((response) => {
        if (!response.ok) throw new Error("Map geometry unavailable");
        return response.json() as Promise<Atlas>;
      })
      .then(setAtlas)
      .catch(() => setError(true));
  }, []);

  const features = useMemo(() => {
    if (!atlas) return [];
    const object = stateFips ? atlas.objects.counties : atlas.objects.states;
    const collection = feature(atlas, object) as unknown as FeatureCollection;
    return collection.features.filter((item) => !stateFips || geometryId(item).startsWith(stateFips));
  }, [atlas, stateFips]);
  const rowByCode = useMemo(() => new Map(rows.map((row) => [row.code, row])), [rows]);
  const values = useMemo(() => rows.map((row) => metricValue(row, metric)).filter((value): value is number => value !== null), [metric, rows]);
  const path = useMemo(() => geoPath(), []);
  const viewBox = useMemo(() => {
    if (!features.length || !stateFips) return "0 0 975 610";
    const bounds = path.bounds({ type: "FeatureCollection", features } as FeatureCollection);
    const pad = 16;
    return `${bounds[0][0] - pad} ${bounds[0][1] - pad} ${bounds[1][0] - bounds[0][0] + pad * 2} ${bounds[1][1] - bounds[0][1] + pad * 2}`;
  }, [features, path, stateFips]);
  const active = activeCode ? rowByCode.get(activeCode) : null;

  if (error) return <div className="grid min-h-[320px] place-items-center rounded-2xl bg-slate-50 px-6 text-center text-sm text-slate-500 dark:bg-slate-950/40 dark:text-slate-400">Map geometry could not be loaded. The ranked market table remains fully available below.</div>;
  if (!atlas) return <div className="min-h-[320px] rounded-2xl skeleton-shimmer" aria-label="Loading map" />;

  return (
    <div className="relative min-h-[300px] overflow-hidden rounded-2xl bg-slate-50 dark:bg-slate-950/40 sm:min-h-[430px]">
      <svg viewBox={viewBox} role="group" aria-label={`${stateFips ? "County" : "State"} choropleth by ${metricLabels[metric]}`} className="h-[300px] w-full sm:h-[430px]">
        {features.map((item) => {
          const code = geometryId(item);
          const row = rowByCode.get(code);
          const d = path(item as Feature<Geometry>) ?? "";
          const interactive = Boolean(row);
          return (
            <path
              key={code}
              d={d}
              fill={fillFor(row ? metricValue(row, metric) : null, values, metric)}
              stroke={activeCode === code || selectedCode === code ? "#0f172a" : "#ffffff"}
              strokeWidth={activeCode === code || selectedCode === code ? 2.2 : stateFips ? 0.6 : 1.1}
              opacity={interactive ? 1 : 0.55}
              tabIndex={interactive ? 0 : undefined}
              role={interactive ? "button" : undefined}
              aria-label={row ? `${row.name}, ${metricLabels[metric]} ${metric === "applicationVolume" ? formatNumber(row.applicationVolume) : formatPercent(metricValue(row, metric) ?? 0)}` : undefined}
              className={interactive ? "cursor-pointer outline-none transition-opacity hover:opacity-80 focus:opacity-80" : undefined}
              onMouseEnter={() => interactive && setActiveCode(code)}
              onMouseLeave={() => setActiveCode(null)}
              onFocus={() => interactive && setActiveCode(code)}
              onBlur={() => setActiveCode(null)}
              onClick={() => row && onSelect(row)}
              onKeyDown={(event) => {
                if (row && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  onSelect(row);
                }
              }}
            />
          );
        })}
      </svg>
      {active ? (
        <div className="pointer-events-none absolute left-4 top-4 max-w-[240px] rounded-xl border border-slate-200 bg-white/95 px-3.5 py-3 shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-900/95">
          <p className="text-sm font-semibold text-slate-950 dark:text-white">{active.name}</p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{metricLabels[metric]} · <strong className="text-slate-800 dark:text-slate-200">{metric === "applicationVolume" ? formatNumber(active.applicationVolume) : formatPercent(metricValue(active, metric) ?? 0)}</strong></p>
          <p className="mt-1 text-[11px] text-slate-400">{formatNumber(active.creditDecisions)} completed decisions</p>
        </div>
      ) : null}
      <div className="absolute bottom-3 right-3 rounded-lg bg-white/90 px-2.5 py-1.5 text-[10px] font-medium text-slate-500 shadow-sm dark:bg-slate-900/90 dark:text-slate-400">Lighter → lower · darker → higher</div>
    </div>
  );
}
