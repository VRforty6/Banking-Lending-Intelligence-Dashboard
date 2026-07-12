import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Union, Tuple, Dict, Any


def clean_chunk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a chunk of HMDA data according to explicit rules.

    Preserve all source columns, but clean specific fields when present.
    """
    # Make a copy to avoid modifying the original
    cleaned = df.copy()

    # Clean activity_year: convert to numeric, then to nullable Int64
    if 'activity_year' in cleaned.columns:
        cleaned['activity_year'] = pd.to_numeric(
            cleaned['activity_year'], errors='coerce'
        ).astype('Int64')

    # Clean action_taken: convert to numeric, then to nullable Int64
    if 'action_taken' in cleaned.columns:
        cleaned['action_taken'] = pd.to_numeric(
            cleaned['action_taken'], errors='coerce'
        ).astype('Int64')

    # Clean loan_amount: convert to numeric, then to nullable Float64
    if 'loan_amount' in cleaned.columns:
        cleaned['loan_amount'] = pd.to_numeric(
            cleaned['loan_amount'], errors='coerce'
        ).astype('Float64')

    # Clean income: convert to numeric, then to nullable Float64
    if 'income' in cleaned.columns:
        cleaned['income'] = pd.to_numeric(
            cleaned['income'], errors='coerce'
        ).astype('Float64')

    # Clean LEI: convert to pandas StringDtype; strip whitespace;
    # replace "", "NA", "N/A", "nan", and "<NA>" with pd.NA;
    # never convert a missing LEI into the literal string "nan"
    if 'lei' in cleaned.columns:
        # Always convert to pandas StringDtype first to avoid numeric conversion
        # which would lose precision and produce scientific notation like 12345678901234.0
        cleaned["lei"] = (
            cleaned["lei"]
                .astype("string")
                .str.strip()
                .replace({
                    "": pd.NA,
                    "NA": pd.NA,
                    "N/A": pd.NA,
                    "nan": pd.NA,
                    "<NA>": pd.NA
                })
        )

    return cleaned


def validate_chunk(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, int]]:
    """
    Validate a chunk of cleaned HMDA data.

    Returns:
        valid_df: DataFrame with rows that pass all validation rules
        rejected_df: DataFrame with rows that fail at least one rule, with rejection_reason column
        counts: Dictionary with counts of each failure type
    """
    # Initialize counters
    counts = {
        'missing_activity_year': 0,
        'missing_lei': 0,
        'invalid_action_taken': 0,
        'invalid_loan_amount': 0
    }

    # Make a copy to avoid modifying the original
    df_copy = df.copy()

    # Initialize rejection_reason as empty string
    df_copy['rejection_reason'] = ''

    # Define conditions in the order they should appear in rejection_reason
    conditions = [
        ('missing_activity_year', df_copy['activity_year'].isna() if 'activity_year' in df_copy.columns else pd.Series(False, index=df_copy.index)),
        ('missing_lei', df_copy['lei'].isna() if 'lei' in df_copy.columns else pd.Series(False, index=df_copy.index)),
        ('invalid_action_taken',
         df_copy['action_taken'].isna() | ~df_copy['action_taken'].between(1, 8) if 'action_taken' in df_copy.columns else pd.Series(False, index=df_copy.index)),
        ('invalid_loan_amount',
         (~df_copy['loan_amount'].isna()) & (df_copy['loan_amount'] <= 0) if 'loan_amount' in df_copy.columns else pd.Series(False, index=df_copy.index))
    ]

    # Build rejection_reason by collecting failed condition names in order
    # We'll create a temporary DataFrame where each column is the condition name if the condition is True, else empty string
    condition_data = {}
    for name, condition in conditions:
        # Count the number of True values for this condition
        counts[name] = condition.sum()
        # For the condition column: put the condition name if True, else empty string
        condition_data[name] = np.where(condition, name, '')

    # Create DataFrame from condition_data
    cond_df = pd.DataFrame(condition_data, index=df_copy.index)
    # Replace empty strings with NaN so we can ignore them when joining
    cond_df = cond_df.replace('', np.nan)
    # For each row, join the non-NaN values with ';' in the order of the columns
    df_copy['rejection_reason'] = cond_df.apply(lambda row: ';'.join(row.dropna().astype(str)), axis=1)

    # Now separate valid and rejected rows
    # Valid rows have empty rejection_reason
    valid_mask = df_copy['rejection_reason'] == ''
    valid_df = df_copy[valid_mask].drop(columns=['rejection_reason'])
    rejected_df = df_copy[~valid_mask]

    return valid_df, rejected_df, counts


def etl_hmda(
    input_path: Union[str, Path],
    output_dir: Union[str, Path],
    chunksize: int = 100_000
) -> Dict[str, int]:
    """
    Execute the HMDA ETL pipeline.

    Args:
        input_path: Path to the input CSV file
        output_dir: Directory where output files will be written
        chunksize: Number of rows to process at a time

    Returns:
        Dictionary with reconciliation counts
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    clean_path = output_dir / 'hmda_clean.parquet'
    rejected_path = output_dir / 'hmda_rejected.parquet'
    report_path = output_dir / 'validation_report.txt'

    # Initialize counters for overall reconciliation
    total_rows = 0
    valid_rows = 0
    rejected_rows = 0
    reason_counts = {
        'missing_activity_year': 0,
        'missing_lei': 0,
        'invalid_action_taken': 0,
        'invalid_loan_amount': 0
    }

    # Initialize Parquet writers (will be set on first chunk)
    clean_writer = None
    rejected_writer = None

    try:
        # Read CSV in chunks
        # Read all columns as string to prevent per-chunk dtype inference
        for chunk_num, chunk in enumerate(
            pd.read_csv(
                input_path,
                chunksize=chunksize,
                low_memory=False,
                keep_default_na=True,
                na_values=["", "NA", "N/A", "Exempt", "nan", "<NA>"],
                dtype="string"
            )
        ):
            total_rows += len(chunk)

            # Clean the chunk
            cleaned_chunk = clean_chunk(chunk)

            # Validate the chunk
            valid_chunk, rejected_chunk, chunk_counts = validate_chunk(cleaned_chunk)

            # Update counters
            valid_rows += len(valid_chunk)
            rejected_rows += len(rejected_chunk)
            for key in reason_counts:
                reason_counts[key] += chunk_counts.get(key, 0)

            # Write valid chunk to Parquet
            if len(valid_chunk) > 0:
                table = pa.Table.from_pandas(
                    valid_chunk.reset_index(drop=True), preserve_index=False
                )
                if clean_writer is None:
                    # Initialize writer with schema from first chunk
                    clean_writer = pq.ParquetWriter(
                        clean_path, table.schema, compression='snappy'
                    )
                else:
                    # Cast the table to the writer's schema
                    table = table.cast(clean_writer.schema, safe=False)
                clean_writer.write_table(table)

            # Write rejected chunk to Parquet
            if len(rejected_chunk) > 0:
                table = pa.Table.from_pandas(
                    rejected_chunk.reset_index(drop=True), preserve_index=False
                )
                if rejected_writer is None:
                    # Initialize writer with schema from first chunk
                    rejected_writer = pq.ParquetWriter(
                        rejected_path, table.schema, compression='snappy'
                    )
                else:
                    # Cast the table to the writer's schema
                    table = table.cast(rejected_writer.schema, safe=False)
                rejected_writer.write_table(table)

    finally:
        # Ensure writers are closed
        if clean_writer is not None:
            clean_writer.close()
        if rejected_writer is not None:
            rejected_writer.close()

    # Calculate reconciliation difference
    reconciliation_difference = total_rows - valid_rows - rejected_rows

    # Write validation report
    with open(report_path, 'w', encoding='utf-8') as f:
       f.write("HMDA ETL Validation Report\n")
       f.write(f"Total rows processed: {total_rows}\n")
       f.write(f"Valid rows: {valid_rows}\n")
       f.write(f"Rejected rows: {rejected_rows}\n")
       f.write(f"Reconciliation difference: {reconciliation_difference}\n")
       f.write(
            f"Failed activity_year (missing): "
            f"{reason_counts['missing_activity_year']}\n"
     )
       f.write(f"Failed lei (missing): {reason_counts['missing_lei']}\n")
       f.write(
           f"Failed loan_amount (invalid): "
           f"{reason_counts['invalid_loan_amount']}\n"
           )
       f.write(
           f"Failed action_taken (invalid): "
           f"{reason_counts['invalid_action_taken']}\n"
        )
    # Return reconciliation counts
    return {
        'total_rows_processed': total_rows,
        'valid_rows': valid_rows,
        'rejected_rows': rejected_rows,
        'reconciliation_difference': reconciliation_difference,
        'failed_activity_year': reason_counts['missing_activity_year'],
        'failed_lei': reason_counts['missing_lei'],
        'failed_loan_amount': reason_counts['invalid_loan_amount'],
        'failed_action_taken': reason_counts['invalid_action_taken']
    }


if __name__ == "__main__":
    # Default paths
    input_path = Path('data/raw/state_CA.csv')
    output_dir = Path('data/processed')

    # Run the ETL
    result = etl_hmda(input_path, output_dir)

    # Print summary
    print("HMDA ETL completed successfully.")
    print(f"Total rows processed: {result['total_rows_processed']}")
    print(f"Valid rows: {result['valid_rows']}")
    print(f"Rejected rows: {result['rejected_rows']}")
    print(f"Reconciliation difference: {result['reconciliation_difference']}")