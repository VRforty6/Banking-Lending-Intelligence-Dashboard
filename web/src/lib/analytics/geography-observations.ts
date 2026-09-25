import type {
  GeographyMetric,
  GeographyMetrics,
  GeographyObservation,
  GeographyRow,
} from "./geography";

const compact = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const metricLabel: Record<GeographyMetric, string> = {
  applicationVolume: "application volume",
  originationRate: "origination rate",
  denialRate: "denial rate",
};

const metricText = (value: number, metric: GeographyMetric) =>
  metric === "applicationVolume" ? compact.format(value) : percent.format(value);

export function buildGeographyObservations({
  rows,
  selectedCode,
  selectedName,
  selectedMetrics,
  parentMetrics,
  metric,
}: {
  rows: GeographyRow[];
  selectedCode: string | null;
  selectedName: string;
  selectedMetrics: GeographyMetrics;
  parentMetrics: GeographyMetrics | null;
  metric: GeographyMetric;
}): GeographyObservation[] {
  if (!rows.length) return [];

  const ranked = [...rows]
    .filter((row) => row[metric] !== null)
    .sort((a, b) => (b[metric] ?? -Infinity) - (a[metric] ?? -Infinity));
  const volumeTotal = rows.reduce((sum, row) => sum + row.applicationVolume, 0);
  const observations: GeographyObservation[] = [];

  if (selectedCode) {
    const selectedRow = rows.find((row) => row.code === selectedCode);
    const rank = ranked.findIndex((row) => row.code === selectedCode) + 1;
    if (selectedRow && rank > 0) {
      observations.push({
        id: "selected-rank",
        label: `${selectedName} ranks #${rank}`,
        detail: `${metricText(selectedRow[metric] ?? 0, metric)} ${metricLabel[metric]} among ${rows.length} peer markets in this view.`,
      });
    }
    if (parentMetrics && parentMetrics.applicationVolume > 0) {
      observations.push({
        id: "selected-share",
        label: `${percent.format(selectedMetrics.applicationVolume / parentMetrics.applicationVolume)} of parent-market volume`,
        detail: `${compact.format(selectedMetrics.applicationVolume)} applications in ${selectedName}, using the established purchased-loan exclusion.`,
      });
    }
    if (parentMetrics?.denialRate != null && selectedMetrics.denialRate !== null) {
      const delta = (selectedMetrics.denialRate - parentMetrics.denialRate) * 100;
      observations.push({
        id: "selected-denial-gap",
        label: `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pp denial-rate gap`,
        detail: `Compared with the parent geography; both rates use completed Credit Decisions as the denominator.`,
      });
    }
    return observations.slice(0, 3);
  }

  const leader = ranked[0];
  if (leader) {
    observations.push({
      id: "metric-leader",
      label: `${leader.name} leads ${metricLabel[metric]}`,
      detail: `${metricText(leader[metric] ?? 0, metric)} with ${compact.format(leader.creditDecisions)} completed Credit Decisions.`,
    });
  }

  if (volumeTotal > 0) {
    const topThreeVolume = [...rows]
      .sort((a, b) => b.applicationVolume - a.applicationVolume)
      .slice(0, 3)
      .reduce((sum, row) => sum + row.applicationVolume, 0);
    observations.push({
      id: "volume-concentration",
      label: `${percent.format(topThreeVolume / volumeTotal)} in the top three markets`,
      detail: `${compact.format(topThreeVolume)} of ${compact.format(volumeTotal)} applications in the current comparison set.`,
    });
  }

  const decisionPeers = [...rows]
    .filter((row) => row.denialRate !== null && row.creditDecisions > 0)
    .sort((a, b) => b.creditDecisions - a.creditDecisions)
    .slice(0, 10);
  if (decisionPeers.length >= 2) {
    const high = decisionPeers.reduce((current, row) =>
      (row.denialRate ?? -Infinity) > (current.denialRate ?? -Infinity)
        ? row
        : current,
    );
    const low = decisionPeers.reduce((current, row) =>
      (row.denialRate ?? Infinity) < (current.denialRate ?? Infinity)
        ? row
        : current,
    );
    observations.push({
      id: "decision-spread",
      label: `${((high.denialRate! - low.denialRate!) * 100).toFixed(1)} pp denial-rate spread`,
      detail: `${high.name} versus ${low.name} among the ten largest markets by Credit Decisions.`,
    });
  }

  return observations.slice(0, 3);
}
