const compactNumber = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const fullNumber = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percent = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const formatCompact = (value: number) => compactNumber.format(value);
export const formatNumber = (value: number) => fullNumber.format(value);
export const formatCurrency = (value: number) => currency.format(value);
export const formatPercent = (value: number) => percent.format(value);

export const formatIncome = (value: number) => `$${fullNumber.format(value)}K`;

export const formatMetric = (
  value: number | null,
  kind: "number" | "percent" | "currency" | "income",
) => {
  if (value === null || !Number.isFinite(value)) return "—";
  if (kind === "percent") return formatPercent(value);
  if (kind === "currency") return formatCurrency(value);
  if (kind === "income") return formatIncome(value);
  return formatCompact(value);
};
