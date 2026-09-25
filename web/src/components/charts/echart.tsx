"use client";

import type { ECharts, EChartsCoreOption } from "echarts";
import { useEffect, useRef } from "react";

export function EChart({
  option,
  className = "h-80",
  onEvents,
  ariaLabel,
}: {
  option: EChartsCoreOption;
  className?: string;
  onEvents?: Record<string, (params: unknown) => void>;
  ariaLabel: string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);

  useEffect(() => {
    let disposed = false;

    const render = async () => {
      if (!containerRef.current) return;
      const echarts = await import("echarts");
      if (disposed || !containerRef.current) return;
      const dark = document.documentElement.classList.contains("dark");
      chartRef.current = echarts.init(containerRef.current, dark ? "dark" : undefined, {
        renderer: "canvas",
      });
      chartRef.current.setOption(option, { notMerge: true });
      Object.entries(onEvents ?? {}).forEach(([event, handler]) => {
        chartRef.current?.on(event, handler);
      });
    };

    void render();

    const resizeObserver = new ResizeObserver(() => chartRef.current?.resize());
    if (containerRef.current) resizeObserver.observe(containerRef.current);

    const handleTheme = () => {
      chartRef.current?.dispose();
      chartRef.current = null;
      void render();
    };
    window.addEventListener("hmda-theme-change", handleTheme);

    return () => {
      disposed = true;
      resizeObserver.disconnect();
      window.removeEventListener("hmda-theme-change", handleTheme);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [onEvents, option]);

  return <div ref={containerRef} className={className} role="img" aria-label={ariaLabel} />;
}
