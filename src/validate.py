"""
Validate module for data quality checks and filtering.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import List, Tuple

from . import config

logger = logging.getLogger(__name__)

def _validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> pd.Series:
    """
    Check for missing values in required columns.

    Returns a boolean Series where True indicates the row is valid (not missing).
    """
    if not required_columns:
        return pd.Series(True, index=df.index)
    mask = pd.Series(True, index=df.index)
    for col in required_columns:
        if col in df.columns:
            mask = mask & df[col].notna()
        else:
            logger.warning(f"Required column '{col}' not found in DataFrame.")
            mask = mask & False
    return mask

def _validate_activity_year(df: pd.DataFrame) -> pd.Series:
    """
    Validate activity_year is in allowed set.
    """
    if 'activity_year' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    activity_year = pd.to_numeric(df['activity_year'], errors='coerce')
    valid_years = getattr(config, 'VALID_YEARS', {2025})
    return activity_year.isna() | activity_year.isin(valid_years)

def _validate_lei(df: pd.DataFrame) -> pd.Series:
    """
    Validate LEI: 20-character alphanumeric string.
    """
    if 'lei' not in df.columns:
        return pd.Series(True, index=df.index)
    lei_series = df['lei']
    null_mask = lei_series.isna()
    # For non-null values, convert to string and validate
    lei_str = lei_series.astype(str)
    length_ok = lei_str.str.len() == 20
    alnum_ok = lei_str.str.match(r'^[A-Z0-9]+$', na=False)
    valid_mask = (~null_mask) & length_ok & alnum_ok
    return null_mask | valid_mask

def _validate_state_code(df: pd.DataFrame) -> pd.Series:
    """
    Validate state_code: two letters.
    """
    if 'state_code' not in df.columns:
        return pd.Series(True, index=df.index)
    state_series = df['state_code']
    null_mask = state_series.isna()
    state_str = state_series.astype(str).str.upper()
    length_ok = state_str.str.len() == 2
    pattern_ok = state_str.str.match(r'^[A-Z]{2}$', na=False)
    valid_mask = (~null_mask) & length_ok & pattern_ok
    return null_mask | valid_mask

def _validate_county_code(df: pd.DataFrame) -> pd.Series:
    """
    Validate county_code: 5 digits.
    """
    if 'county_code' not in df.columns:
        return pd.Series(True, index=df.index)
    county_series = df['county_code']
    null_mask = county_series.isna()
    county_str = county_series.astype(str)
    length_ok = county_str.str.len() == 5
    pattern_ok = county_str.str.match(r'^\d{5}$', na=False)
    valid_mask = (~null_mask) & length_ok & pattern_ok
    return null_mask | valid_mask

def _validate_census_tract(df: pd.DataFrame) -> pd.Series:
    """
    Validate census_tract: 11 digits.
    """
    if 'census_tract' not in df.columns:
        return pd.Series(True, index=df.index)
    tract_series = df['census_tract']
    null_mask = tract_series.isna()
    tract_str = tract_series.astype(str)
    length_ok = tract_str.str.len() == 11
    pattern_ok = tract_str.str.match(r'^\d{11}$', na=False)
    valid_mask = (~null_mask) & length_ok & pattern_ok
    return null_mask | valid_mask

def _validate_loan_amount(df: pd.DataFrame) -> pd.Series:
    """
    Validate loan_amount: positive when present.
    """
    if 'loan_amount' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    loan_amount = pd.to_numeric(df['loan_amount'], errors='coerce')
    return loan_amount.isna() | (loan_amount > 0)

def _validate_income(df: pd.DataFrame) -> pd.Series:
    """
    Validate income: non-negative when present.
    """
    if 'income' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    income = pd.to_numeric(df['income'], errors='coerce')
    return income.isna() | (income >= 0)

def _validate_age(df: pd.DataFrame, column_name: str) -> pd.Series:
    """
    Validate age: between 0 and 110 inclusive when present.
    """
    if column_name not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    age = pd.to_numeric(df[column_name], errors='coerce')
    return age.isna() | ((age >= 0) & (age <= 110))

def _validate_ltv(df: pd.DataFrame) -> pd.Series:
    """
    Validate loan_to_value_ratio: between 0 and 500.
    """
    if 'loan_to_value_ratio' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    ltv = pd.to_numeric(df['loan_to_value_ratio'], errors='coerce')
    return ltv.isna() | ((ltv >= 0) & (ltv <= 500))

def _validate_dti(df: pd.DataFrame) -> pd.Series:
    """
    Validate debt_to_income_ratio: between 0 and 1000? We'll allow up to 1000.
    """
    if 'debt_to_income_ratio' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    dti = pd.to_numeric(df['debt_to_income_ratio'], errors='coerce')
    return dti.isna() | ((dti >= 0) & (dti <= 1000))

def _validate_interest_rate(df: pd.DataFrame) -> pd.Series:
    """
    Validate interest_rate: between 0 and 30.
    """
    if 'interest_rate' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    interest_rate = pd.to_numeric(df['interest_rate'], errors='coerce')
    return interest_rate.isna() | ((interest_rate >= 0) & (interest_rate <= 30))

def _validate_rate_spread(df: pd.DataFrame) -> pd.Series:
    """
    Validate rate_spread: between -10 and 30? We'll be lenient.
    """
    if 'rate_spread' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    rate_spread = pd.to_numeric(df['rate_spread'], errors='coerce')
    return rate_spread.isna() | (rate_spread >= -10) & (rate_spread <= 30)

def _validate_hoepa_status(df: pd.DataFrame) -> pd.Series:
    """
    Validate hoepa_status: 1, 2, or 3.
    """
    if 'hoepa_status' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    hoepa_status = pd.to_numeric(df['hoepa_status'], errors='coerce')
    return hoepa_status.isna() | hoepa_status.isin([1, 2, 3])

def _validate_action_taken(df: pd.DataFrame) -> pd.Series:
    """
    Validate action_taken: 1 through 8.
    """
    if 'action_taken' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    action_taken = pd.to_numeric(df['action_taken'], errors='coerce')
    return action_taken.isna() | action_taken.isin(range(1, 9))  # 1 to 8 inclusive

def _validate_loan_type(df: pd.DataFrame) -> pd.Series:
    """
    Validate loan_type: 1, 2, 3, 4.
    """
    if 'loan_type' not in df.columns:
        return pd.Series(True, index=df.index)
    # Convert to numeric, coercing errors to NaN
    loan_type = pd.to_numeric(df['loan_type'], errors='coerce')
    return loan_type.isna() | loan_type.isin([1, 2, 3, 4])

def _validate_loan_purpose(df: pd.DataFrame) -> pd.Series:
    """
    Validate loan_purpose: 1, 2, 3.
    """
    if 'loan_purpose' not in df.columns:
        return pd.Series(False, index=df.index)
    # Convert to numeric, coercing errors to NaN
    loan_purpose = pd.to_numeric(df['loan_purpose'], errors='coerce')
    return loan_purpose.isna() | loan_purpose.isin([1, 2, 3])

def _validate_lien_status(df: pd.DataFrame) -> pd.Series:
    """
    Validate lien_status: 1, 2, 3.
    """
    if 'lien_status' not in df.columns:
        return pd.Series(False, index=df.index)
    # Convert to numeric, coercing errors to NaN
    lien_status = pd.to_numeric(df['lien_status'], errors='coerce')
    return lien_status.isna() | lien_status.isin([1, 2, 3])

def validate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Validate a DataFrame, splitting into valid and rejected rows.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to validate.

    Returns
    -------
    valid_df : pd.DataFrame
        Rows that passed all validation checks.
    rejected_df : pd.DataFrame
        Rows that failed at least one validation, with a 'rejection_reason' column.
    stats : dict
        Dictionary with counts of total, valid, rejected, and counts per validation rule.
    """
    logger.info("Starting validation of DataFrame.")
    total_rows = len(df)
    if total_rows == 0:
        logger.warning("DataFrame is empty.")
        return df.copy(), pd.DataFrame(), {'total': 0, 'valid': 0, 'rejected': 0}

    # We'll collect a list of boolean series, each indicating violation of a rule.
    # We'll also keep a mapping from rule name to the series.
    validation_rules = []

    # Required fields: we consider these as critical and must not be null.
    # Based on the data dictionary, we'll choose a set of key fields.
    required_columns = [
        'activity_year', 'lei', 'census_tract', 'loan_amount', 'action_taken'
    ]
    validation_rules.append(('required_not_null', _validate_required_columns(df, required_columns)))

    # Individual field validations
    validation_rules.append(('activity_year', _validate_activity_year(df)))
    validation_rules.append(('lei', _validate_lei(df)))
    validation_rules.append(('state_code', _validate_state_code(df)))
    validation_rules.append(('county_code', _validate_county_code(df)))
    validation_rules.append(('census_tract', _validate_census_tract(df)))
    validation_rules.append(('loan_amount', _validate_loan_amount(df)))
    validation_rules.append(('income', _validate_income(df)))
    validation_rules.append(('applicant_age', _validate_age(df, 'applicant_age')))
    validation_rules.append(('co_applicant_age', _validate_age(df, 'co_applicant_age')))
    validation_rules.append(('loan_to_value_ratio', _validate_ltv(df)))
    validation_rules.append(('debt_to_income_ratio', _validate_dti(df)))
    validation_rules.append(('interest_rate', _validate_interest_rate(df)))
    validation_rules.append(('rate_spread', _validate_rate_spread(df)))
    validation_rules.append(('hoepa_status', _validate_hoepa_status(df)))
    validation_rules.append(('action_taken', _validate_action_taken(df)))
    validation_rules.append(('loan_type', _validate_loan_type(df)))
    validation_rules.append(('loan_purpose', _validate_loan_purpose(df)))
    validation_rules.append(('lien_status', _validate_lien_status(df)))

    # Combine all validations: a row is valid if it passes ALL rules.
    # We'll compute a DataFrame where each column is a rule's pass/fail (True=pass).
    validation_df = pd.DataFrame({name: series for name, series in validation_rules}, index=df.index)
    # For each row, we need all to be True.
    passed_all = validation_df.all(axis=1)

    # Valid rows: those that passed all checks
    valid_df = df[passed_all].copy()
    # Rejected rows: those that failed at least one check
    rejected_mask = ~passed_all
    rejected_df = df[rejected_mask].copy()

    # For rejected rows, we want to provide a reason.
    # For each rejected row, we'll collect the names of the rules that failed.
    def get_failure_reasons(row_idx):
        failed_rules = []
        for rule_name, series in validation_rules:
            if not series.loc[row_idx]:
                failed_rules.append(rule_name)
        return "; ".join(failed_rules)

    if not rejected_df.empty:
        rejected_df['rejection_reason'] = [
            get_failure_reasons(idx) for idx in rejected_df.index
        ]
    else:
        rejected_df['rejection_reason'] = pd.Series(dtype='str')

    # Statistics
    stats = {
        'total': total_rows,
        'valid': len(valid_df),
        'rejected': len(rejected_df),
        'rejection_rate': len(rejected_df) / total_rows if total_rows > 0 else 0
    }
    # Add per-rule failure counts
    for rule_name, series in validation_rules:
        failed_count = (~series).sum()
        stats[f'failed_{rule_name}'] = int(failed_count)
        logger.info(f"Validation rule '{rule_name}' failed on {failed_count} rows")

    logger.info(f"Validation complete: {len(valid_df)} valid, {len(rejected_df)} rejected out of {total_rows} total.")
    return valid_df, rejected_df, stats