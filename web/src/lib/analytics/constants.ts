export const YEARS = [2023, 2024, 2025] as const;

export const STATES = [
  { value: "CA", label: "California", fips: "06" },
  { value: "FL", label: "Florida", fips: "12" },
  { value: "IL", label: "Illinois", fips: "17" },
  { value: "NY", label: "New York", fips: "36" },
  { value: "TX", label: "Texas", fips: "48" },
] as const;

export const LOAN_PURPOSES = [
  { value: "1", label: "Home purchase" },
  { value: "2", label: "Home improvement" },
  { value: "31", label: "Refinancing" },
  { value: "32", label: "Cash-out refinancing" },
  { value: "4", label: "Other purpose" },
  { value: "5", label: "Not applicable" },
] as const;

export const ACTION_LABELS: Record<number, string> = {
  1: "Originated",
  2: "Approved, not accepted",
  3: "Denied",
  4: "Withdrawn",
  5: "Closed for incompleteness",
  6: "Purchased loan",
  7: "Preapproval denied",
  8: "Preapproval approved, not accepted",
};

export const METRIC_DEFINITIONS = [
  {
    name: "Application Volume",
    definition: "HMDA action codes 1-5, 7, and 8; purchased loans (code 6) are excluded.",
  },
  {
    name: "Credit Decisions",
    definition: "Completed decisions with action codes 1, 2, and 3.",
  },
  {
    name: "Origination Rate",
    definition: "Originated applications (code 1) divided by Credit Decisions.",
  },
  {
    name: "Denial Rate",
    definition: "Denied applications (code 3) divided by Credit Decisions.",
  },
  {
    name: "Average Originated Loan Amount",
    definition: "Average loan amount for originated applications only (action code 1).",
  },
  {
    name: "Median Applicant Income",
    definition: "Median reported applicant income. HMDA income is stored in thousands of dollars.",
  },
] as const;
