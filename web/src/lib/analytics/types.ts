export type FilterValue = string | null;

export interface ExecutiveFilters {
  year: number | null;
  state: string | null;
  loanPurpose: string | null;
}

export interface MetricValue {
  value: number | null;
  numerator?: number;
  denominator?: number;
}

export interface ExecutiveData {
  hasData: boolean;
  filters: ExecutiveFilters;
  options: {
    years: number[];
    states: Array<{ value: string; label: string }>;
    loanPurposes: Array<{ value: string; label: string }>;
  };
  kpis: {
    applicationVolume: MetricValue;
    originationRate: MetricValue;
    denialRate: MetricValue;
    averageOriginatedLoanAmount: MetricValue;
    medianApplicantIncome: MetricValue;
  };
  context: {
    totalHmdaRecords: number;
    creditDecisions: number;
    purchasedLoans: number;
    refreshedAt: string;
  };
  trend: Array<{
    year: number;
    applicationVolume: number;
    originations: number;
    denials: number;
    creditDecisions: number;
    originationRate: number | null;
    denialRate: number | null;
  }>;
  outcomes: Array<{ code: number; label: string; value: number }>;
  loanPurposes: Array<{ code: string; label: string; value: number }>;
  states: Array<{
    code: string;
    label: string;
    applicationVolume: number;
    originationRate: number | null;
    denialRate: number | null;
  }>;
  topLenders: Array<{
    lei: string;
    label: string;
    applicationVolume: number;
  }>;
  topCounties: Array<{
    state: string;
    county: string;
    label: string;
    applicationVolume: number;
  }>;
  definitions: Array<{
    name: string;
    definition: string;
  }>;
}
