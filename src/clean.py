"""
Clean module for standardizing column names and data types.
"""

import pandas as pd
import numpy as np
import re
from typing import List, Dict
import logging

from . import config

logger = logging.getLogger(__name__)

# Columns that are integer codes (categorical)
INTEGER_CODE_COLUMNS = {
    'action_taken',
    'purchaser_type',
    'preapproval',
    'loan_type',
    'loan_purpose',
    'lien_status',
    'reverse_mortgage',
    'open_end_line_of_credit',
    'business_or_commercial_purpose',
    'hoepa_status',
    'construction_method',
    'occupancy_type',
    'applicant_credit_score_type',
    'co_applicant_credit_score_type',
    'applicant_sex',
    'co_applicant_sex',
    'submission_of_application',
    'initially_payable_to_institution',
    'denial_reason_1',
    'denial_reason_2',
    'denial_reason_3',
    'denial_reason_4'
}

# Numeric columns that should be stored as nullable integer (Int64) after cleaning
INTEGER_NUMERIC_COLUMNS = {
    'activity_year'
}

# Exact numeric column names that do not match the common patterns
EXPLICIT_NUMERIC_COLUMNS = {
    'income'
}

def _get_column_type(col_name: str) -> str:
    """
    Determine the expected type of a column based on its name.
    Returns one of: 'numeric', 'integer_code', 'string'
    """
    # Convert to lower case for matching
    lower_col = col_name.lower()

    # Columns that are known integer-coded fields (except year) should be integer_code
    if col_name in INTEGER_CODE_COLUMNS:
        return 'integer_code'

    # Exact numeric fields (e.g., income) that should be treated as numeric
    if col_name in EXPLICIT_NUMERIC_COLUMNS:
        return 'numeric'

    # Numeric patterns: keywords that indicate numeric fields
    numeric_patterns = [
        '_amount', '_value', '_ratio', '_rate', '_percent', '_income',
        '_score', '_age', '_year', '_limit', '_fee', '_cost', '_points',
        '_payment', '_penalty', '_period', '_units', '_population'
    ]
    if any(pattern in lower_col for pattern in numeric_patterns):
        return 'numeric'

    # If none of the above, treat as string
    return 'string'

def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names: lowercase, replace spaces and hyphens with underscores.
    """
    new_columns = []
    for col in df.columns:
        # Strip whitespace
        clean = col.strip()
        # Convert to lowercase
        clean = clean.lower()
        # Replace hyphens and spaces with underscores
        clean = re.sub(r'[\s-]+', '_', clean)
        # Remove any duplicate underscores
        clean = re.sub(r'_+', '_', clean)
        # Remove leading/trailing underscores
        clean = clean.strip('_')
        new_columns.append(clean)
    df.columns = new_columns
    return df

def _clean_numeric_column(series: pd.Series, col_name: str) -> pd.Series:
    """
    Convert a series to numeric, treating 'NA' as NaN.
    """
    # Replace 'NA' string with NaN
    series = series.replace(config.HMDA_NA_STRING, np.nan)
    # Convert to numeric, coercing errors to NaN
    return pd.to_numeric(series, errors='coerce')

def _clean_categorical_column(series: pd.Series) -> pd.Series:
    """
    Convert a series to nullable integer (Int64), treating 'NA' as NaN.
    """
    # Replace 'NA' string with NaN
    series = series.replace(config.HMDA_NA_STRING, np.nan)
    # Convert to Int64 (nullable integer)
    return pd.to_numeric(series, errors='coerce').astype('Int64')

def _clean_string_column(series: pd.Series) -> pd.Series:
    """
    Clean a string series: strip whitespace, convert 'NA' to NaN (or empty string?).
    We'll convert 'NA' to NaN and then fill with empty string? Or keep as NaN.
    We'll keep as NaN for missing string values.
    """
    # Strip whitespace
    series = series.str.strip()
    # Replace 'NA' string with NaN
    series = series.replace(config.HMDA_NA_STRING, np.nan)
    return series

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a DataFrame: standardize column names and convert data types.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame as read from CSV (all columns as string).

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with standardized column names and appropriate types.
    """
    logger.info("Starting data cleaning process.")

    # Step 1: Standardize column names
    df = _clean_column_names(df)
    logger.info(f"Standardized column names. New columns: {list(df.columns)}")

    # Step 2: For each column, determine type and clean accordingly
    cleaned_columns = {}
    for col in df.columns:
        col_type = _get_column_type(col)
        series = df[col]
        if col_type == 'numeric':
            numeric_series = _clean_numeric_column(series, col)
            if col in INTEGER_NUMERIC_COLUMNS:
                cleaned_series = numeric_series.astype('Int64')
            else:
                cleaned_series = numeric_series
            logged_msg = f"Column '{col}' treated as numeric."
        elif col_type == 'integer_code':
            numeric_series = _clean_numeric_column(series, col)
            # integer_code columns should be Int64
            cleaned_series = numeric_series.astype('Int64')
            logged_msg = f"Column '{col}' treated as integer code."
        else:  # string
            cleaned_series = _clean_string_column(series)
            logged_msg = f"Column '{col}' treated as string."
        cleaned_columns[col] = cleaned_series
        logger.debug(logged_msg)

    # Reconstruct DataFrame
    cleaned_df = pd.DataFrame(cleaned_columns)
    logger.info("Data cleaning completed.")
    return cleaned_df