import { describe, expect, it } from "vitest";

import type { GeographyMetrics, GeographyRow } from "./geography";
import { buildGeographyObservations } from "./geography-observations";

const metrics = (overrides: Partial<GeographyMetrics> = {}): GeographyMetrics => ({
  totalHmdaRecords: 100,
  applicationVolume: 90,
  creditDecisions: 80,
  originations: 56,
  denials: 20,
  originationRate: 0.7,
  denialRate: 0.25,
  ...overrides,
});

const row = (code: string, name: string, volume: number, denialRate: number): GeographyRow => ({
  ...metrics({
    applicationVolume: volume,
    creditDecisions: volume,
    originations: volume * (1 - denialRate),
    denials: volume * denialRate,
    originationRate: 1 - denialRate,
    denialRate,
  }),
  code,
  state: code.slice(0, 2),
  name,
  level: "state",
  mapped: true,
});

describe("geographic observations", () => {
  const rows = [
    row("06", "California", 500, 0.2),
    row("48", "Texas", 300, 0.3),
    row("12", "Florida", 200, 0.4),
  ];

  it("derives deterministic leader, concentration, and spread observations", () => {
    const observations = buildGeographyObservations({
      rows,
      selectedCode: null,
      selectedName: "United States",
      selectedMetrics: metrics(),
      parentMetrics: null,
      metric: "applicationVolume",
    });
    expect(observations.map((item) => item.id)).toEqual([
      "metric-leader",
      "volume-concentration",
      "decision-spread",
    ]);
    expect(observations[0].label).toContain("California");
  });

  it("compares a selection with its parent geography", () => {
    const observations = buildGeographyObservations({
      rows,
      selectedCode: "48",
      selectedName: "Texas",
      selectedMetrics: metrics({ applicationVolume: 300, denialRate: 0.3 }),
      parentMetrics: metrics({ applicationVolume: 1000, denialRate: 0.25 }),
      metric: "denialRate",
    });
    expect(observations[0].label).toContain("#2");
    expect(observations[1].label).toContain("30.0%");
    expect(observations[2].label).toBe("+5.0 pp denial-rate gap");
  });

  it("does not invent observations for an empty comparison", () => {
    expect(
      buildGeographyObservations({
        rows: [],
        selectedCode: null,
        selectedName: "United States",
        selectedMetrics: metrics(),
        parentMetrics: null,
        metric: "applicationVolume",
      }),
    ).toEqual([]);
  });
});
