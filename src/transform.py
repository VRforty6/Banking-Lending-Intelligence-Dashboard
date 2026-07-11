"""
Transform module for decoding coded fields using lookup tables.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import logging

from . import config

logger = logging.getLogger(__name__)

def _load_lookup_table(table_name: str) -> pd.DataFrame:
    """
    Load a lookup table from the lookup directory.

    Expected file format: CSV with columns 'code' and 'description'.
    The code column can be integer or string; we'll keep as string for merging.

    Parameters
    ----------
    table_name : str
        Name of the lookup table (without extension). The file should be named {table_name}.csv
        and located in config.RAW_DATA_DIR / 'lookup'.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns 'code' and 'description'.
    """
    lookup_dir = Path(config.LOOKUP_DATA_DIR)
    file_path = lookup_dir / f"{table_name}.csv"
    if not file_path.exists():
        logger.warning(f"Lookup table not found: {file_path}. Skipping.")
        return pd.DataFrame(columns=['code', 'description'])
    try:
        df = pd.read_csv(file_path, dtype=str)  # read as string to preserve leading zeros
        # Ensure required columns exist
        if 'code' not in df.columns or 'description' not in df.columns:
            # Try to infer: first column as code, second as description
            if len(df.columns) >= 2:
                df = df.rename(columns={df.columns[0]: 'code', df.columns[1]: 'description'})
            else:
                raise ValueError(f"Lookup table {file_path} must have at least two columns.")
        # Keep only code and description
        df = df[['code', 'description']].copy()
        # Strip whitespace from code and description
        df['code'] = df['code'].str.strip()
        df['description'] = df['description'].str.strip()
        logger.info(f"Loaded lookup table '{table_name}' with {len(df)} entries.")
        return df
    except Exception as e:
        logger.error(f"Failed to load lookup table {file_path}: {e}")
        return pd.DataFrame(columns=['code', 'description'])

def _apply_lookup(df: pd.DataFrame, column_name: str, lookup_table_name: str) -> pd.DataFrame:
    """
    Apply a lookup table to a column, adding a new column with the description.

    The new column will be named: {column_name}_description

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column_name : str
        The column containing codes to look up.
    lookup_table_name : str
        The name of the lookup table (without extension).

    Returns
    -------
    pd.DataFrame
        DataFrame with an additional column for the description.
    """
    if column_name not in df.columns:
        logger.warning(f"Column '{column_name}' not found in DataFrame. Skipping lookup.")
        return df

    lookup_df = _load_lookup_table(lookup_table_name)
    if lookup_df.empty:
        # No lookup table, skip
        return df

    # Ensure the code column in lookup is string for merging
    lookup_df['code'] = lookup_df['code'].astype(str)
    # Convert the column in df to string (handling NaN)
    # We'll create a temporary series for merge
    temp_series = df[column_name].astype(str).where(df[column_name].notna(), None)
    # We cannot merge directly with NaN, so we'll fill NaN with a placeholder?
    # Instead, we'll do a left join on the code, but we need to handle missing.
    # We'll create a copy of the column as string, and for NaN we'll keep as NaN in the result.
    # We'll do a left merge on the code, but we need to convert the column to string and fill NaN with a placeholder that won't match.
    # Let's do: create a temporary key column that is string of the code, and for NaN we set to empty string (or a special string) that won't be in lookup.
    # Then after merge, we'll set the description to NaN where the original was NaN.

    # Create a temporary key
    temp_key = df[column_name].copy()
    # Convert to string, but keep NaN as NaN
    # We'll use: if not null, convert to string, else keep as NaN
    # Actually, we can't have NaN in a string column for merge. We'll convert to string and replace 'nan' with a placeholder.
    # Better: we'll do a left join using merge on the code, but we need to have the same type.
    # We'll convert the column to string and fill NaN with a special string that we know is not in the lookup (like '__MISSING__')
    # Then after the merge, we'll set the description back to NaN where the original was NaN.

    placeholder = '__MISSING__'
    # Convert to string, fill NaN with placeholder
    key_series = df[column_name].astype(str).fillna(placeholder)
    # Create a temporary DataFrame for merging
    merge_df = pd.DataFrame({column_name: key_series}, index=df.index)
    # Merge with lookup
    merged = merge_df.merge(lookup_df, left_on=column_name, right_on='code', how='left')
    # Extract the description column
    description_series = merged['description']
    # Replace rows where the original was NaN (or placeholder) with NaN in description
    # Actually, where key_series == placeholder, we want description to be NaN
    description_series = description_series.where(key_series != placeholder, other=np.nan)
    # Assign to new column
    new_column_name = f"{column_name}_description"
    df[new_column_name] = description_series.values
    logger.info(f"Applied lookup '{lookup_table_name}' to column '{column_name}', created '{new_column_name}'.")
    return df

def decode_categorical_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Decode known categorical fields using lookup tables.

    This function will look for common HMDA coded columns and apply the corresponding lookup.
    If a lookup table is not found, it will skip and log a warning.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with coded columns as integers (or NaN).

    Returns
    -------
    pd.DataFrame
        DataFrame with additional description columns for each decoded field.
    """
    logger.info("Starting decoding of categorical fields using lookup tables.")

    # Mapping from column name to lookup table name (without .csv)
    # We'll define a dictionary for known mappings.
    # Note: the column names are already cleaned (lowercase, underscores).
    column_to_lookup = {
        'action_taken': 'action_taken',
        'loan_type': 'loan_type',
        'loan_purpose': 'loan_purpose',
        'lien_status': 'lien_status',
        'reverse_mortgage': 'reverse_mortgage',
        'open_end_line_of_credit': 'open_end_line_of_credit',  # note: original had hyphen, we converted to underscore
        'business_or_commercial_purpose': 'business_or_commercial_purpose',
        'hoepa_status': 'hoepa_status',
        'negative_amortization': 'negative_amortization',
        'interest_only_payment': 'interest_only_payment',
        'balloon_payment': 'balloon_payment',
        'other_nonamortizing_features': 'other_nonanomortizing_features',
        'construction_method': 'construction_method',
        'occupancy_type': 'occupancy_type',
        'manufactured_home_secured_property_type': 'manufactured_home_secured_property_type',
        'manufactured_home_land_property_interest': 'manufactured_home_land_property_interest',
        'applicant_credit_score_type': 'applicant_credit_score_type',
        'co_applicant_credit_score_type': 'co_applicant_credit_score_type',
        # Ethnicity and race: we have multiple fields (applicant_ethnicity-1, etc.)
        # We'll handle them separately.
    }

    # Apply lookup for each known column
    for col, lookup_name in column_to_lookup.items():
        if col in df.columns:
            df = _apply_lookup(df, col, lookup_name)
        else:
            logger.debug(f"Column '{col}' not found in DataFrame, skipping lookup.")

    # Handle applicant_ethnicity-1 through -5 and co-applicant_ethnicity-1 through -5
    # We'll create a list of these columns
    ethnicity_cols = [f'applicant_ethnicity_{i}' for i in range(1, 6)] + \
                     [f'co_applicant_ethnicity_{i}' for i in range(1, 6)]
    for col in ethnicity_cols:
        if col in df.columns:
            df = _apply_lookup(df, col, 'ethnicity')
        else:
            logger.debug(f"Column '{col}' not found in DataFrame, skipping ethnicity lookup.")

    # Similarly for race
    race_cols = [f'applicant_race_{i}' for i in range(1, 6)] + \
                [f'co_applicant_race_{i}' for i in range(1, 6)]
    for col in race_cols:
        if col in df.columns:
            df = _apply_lookup(df, col, 'race')
        else:
            logger.debug(f"Column '{col}' not found in DataFrame, skipping race lookup.")

    # Sex observed fields
    sex_obs_cols = ['applicant_sex_observed', 'co_applicant_sex_observed']
    for col in sex_obs_cols:
        if col in df.columns:
            df = _apply_lookup(df, col, 'sex')
        else:
            logger.debug(f"Column '{col}' not found in DataFrame, skipping sex observed lookup.")

    # Note: we also have derived_ethnicity, derived_race, derived_sex
    # These are also coded.
    derived_cols = {
        'derived_ethnicity': 'ethnicity',
        'derived_race': 'race',
        'derived_sex': 'sex'
    }
    for col, lookup_name in derived_cols.items():
        if col in df.columns:
            df = _apply_lookup(df, col, lookup_name)
        else:
            logger.debug(f"Column '{col}' not found in DataFrame, skipping derived lookup.")

    logger.info("Decoding of categorical fields completed.")
    return df

def transform_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all transformation steps to the DataFrame.

    Currently, this includes decoding categorical fields using lookup tables.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame.

    Returns
    -------
    pd.DataFrame
        Transformed DataFrame with decoded fields.
    """
    logger.info("Starting transformation process.")
    df = decode_categorical_fields(df)
    logger.info("Transformation process completed.")
    return df