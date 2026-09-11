import pandas as pd
import numpy as np
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Union, Tuple, Dict, Any, List, Optional

from src import config


HMDA_FILE_RE = re.compile(r"^hmda_(?P<year>\d{4})_(?P<state>[A-Za-z]{2})\.csv$")
NA_VALUES = ["", "NA", "N/A", "Exempt", "nan", "<NA>"]


@dataclass(frozen=True)
class HmdaSourceFile:
    path: Path
    year: int
    state: str


def parse_hmda_filename(path: Union[str, Path]) -> Optional[HmdaSourceFile]:
    """Parse hmda_<YEAR>_<STATE>.csv names, returning None for other names."""
    path = Path(path)
    match = HMDA_FILE_RE.match(path.name)
    if not match:
        return None
    return HmdaSourceFile(
        path=path,
        year=int(match.group("year")),
        state=match.group("state").upper(),
    )


def discover_hmda_files(
    raw_dir: Union[str, Path],
    valid_years: set[int] = config.VALID_YEARS,
    supported_states: set[str] = config.SUPPORTED_STATES,
) -> List[HmdaSourceFile]:
    """
    Discover supported HMDA raw CSVs using hmda_<YEAR>_<STATE>.csv names.

    Files that follow the naming convention but fall outside the supported scope
    fail clearly so an operator does not accidentally skip a state-year extract.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    discovered: list[HmdaSourceFile] = []
    unsupported: list[str] = []
    for path in sorted(raw_dir.glob(config.RAW_FILE_PATTERN)):
        source = parse_hmda_filename(path)
        if source is None:
            continue
        if source.year not in valid_years or source.state not in supported_states:
            unsupported.append(path.name)
            continue
        discovered.append(source)

    if unsupported:
        raise ValueError(
            "Unsupported HMDA raw file(s): "
            + ", ".join(unsupported)
            + f". Supported years: {sorted(valid_years)}; "
            + f"supported states: {sorted(supported_states)}"
        )

    if not discovered:
        raise FileNotFoundError(
            f"No supported HMDA CSV files found in {raw_dir} using "
            "hmda_<YEAR>_<STATE>.csv"
        )

    return discovered


def _empty_count_bucket() -> Dict[str, int]:
    return {"total_rows": 0, "valid_rows": 0, "rejected_rows": 0}


def _update_bucket(bucket: Dict[str, int], total: int, valid: int, rejected: int) -> None:
    bucket["total_rows"] += total
    bucket["valid_rows"] += valid
    bucket["rejected_rows"] += rejected


def validate_source_metadata(
    df: pd.DataFrame,
    source: HmdaSourceFile,
    chunk_num: int,
) -> None:
    """
    Ensure activity_year and state_code agree with the source filename.

    The ETL fails fast on mismatches rather than rewriting source values or
    blending a mislabeled file into the consolidated Parquet output.
    """
    required_columns = ["activity_year", "state_code"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"{source.path.name} is missing required metadata column(s): "
            f"{', '.join(missing_columns)}"
        )

    year_values = pd.to_numeric(df["activity_year"], errors="coerce")
    bad_year_mask = year_values.isna() | (year_values != source.year)
    if bad_year_mask.any():
        sample = (
            df.loc[bad_year_mask, "activity_year"]
            .astype("string")
            .drop_duplicates()
            .head(5)
            .tolist()
        )
        raise ValueError(
            f"{source.path.name} chunk {chunk_num} has activity_year values "
            f"that do not match filename year {source.year}: {sample}"
        )

    state_values = df["state_code"].astype("string").str.strip().str.upper()
    bad_state_mask = state_values.isna() | (state_values != source.state)
    if bad_state_mask.any():
        sample = (
            df.loc[bad_state_mask, "state_code"]
            .astype("string")
            .drop_duplicates()
            .head(5)
            .tolist()
        )
        raise ValueError(
            f"{source.path.name} chunk {chunk_num} has state_code values "
            f"that do not match filename state {source.state}: {sample}"
        )


def _ensure_schema_compatible(
    table: pa.Table,
    writer: pq.ParquetWriter,
    dataset_name: str,
) -> pa.Table:
    if table.schema.names != writer.schema.names:
        raise ValueError(
            f"{dataset_name} schema mismatch. Expected columns "
            f"{writer.schema.names}, received {table.schema.names}"
        )
    return table.cast(writer.schema, safe=False)


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
) -> Dict[str, Any]:
    """
    Execute the HMDA ETL pipeline.

    Args:
        input_path: Path to an input CSV file or a raw data directory
        output_dir: Directory where output files will be written
        chunksize: Number of rows to process at a time

    Returns:
        Dictionary with reconciliation counts
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define output paths
    clean_path = output_dir / config.CLEANED_FILE_NAME
    rejected_path = output_dir / config.REJECTED_FILE_NAME
    report_path = output_dir / config.REPORT_FILE_NAME

    for output_path in [clean_path, rejected_path, report_path]:
        if output_path.exists():
            output_path.unlink()

    if input_path.is_dir():
        sources = [(source.path, source) for source in discover_hmda_files(input_path)]
    elif input_path.is_file():
        source = parse_hmda_filename(input_path)
        if source is not None:
            if source.year not in config.VALID_YEARS or source.state not in config.SUPPORTED_STATES:
                raise ValueError(
                    f"Unsupported HMDA raw file: {input_path.name}. "
                    f"Supported years: {sorted(config.VALID_YEARS)}; "
                    f"supported states: {sorted(config.SUPPORTED_STATES)}"
                )
        sources = [(input_path, source)]
    else:
        raise FileNotFoundError(f"Input path not found: {input_path}")

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
    counts_by_source_file: dict[str, dict[str, int]] = defaultdict(_empty_count_bucket)
    counts_by_year: dict[int, dict[str, int]] = defaultdict(_empty_count_bucket)
    counts_by_state: dict[str, dict[str, int]] = defaultdict(_empty_count_bucket)

    # Initialize Parquet writers (will be set on first chunk)
    clean_writer = None
    rejected_writer = None

    try:
        for source_path, source_metadata in sources:
            # Read CSV in chunks. Read all columns as string to prevent
            # per-chunk dtype inference and keep RAM bounded.
            for chunk_num, chunk in enumerate(
                pd.read_csv(
                    source_path,
                    chunksize=chunksize,
                    low_memory=False,
                    keep_default_na=True,
                    na_values=NA_VALUES,
                    dtype="string"
                )
            , start=1):
                input_count = len(chunk)
                total_rows += input_count

                # Clean the chunk
                cleaned_chunk = clean_chunk(chunk)

                if source_metadata is not None:
                    validate_source_metadata(cleaned_chunk, source_metadata, chunk_num)

                # Validate the chunk
                valid_chunk, rejected_chunk, chunk_counts = validate_chunk(cleaned_chunk)

                valid_count = len(valid_chunk)
                rejected_count = len(rejected_chunk)

                # Update counters
                valid_rows += valid_count
                rejected_rows += rejected_count
                for key in reason_counts:
                    reason_counts[key] += int(chunk_counts.get(key, 0))

                _update_bucket(
                    counts_by_source_file[source_path.name],
                    input_count,
                    valid_count,
                    rejected_count,
                )
                if source_metadata is not None:
                    _update_bucket(
                        counts_by_year[source_metadata.year],
                        input_count,
                        valid_count,
                        rejected_count,
                    )
                    _update_bucket(
                        counts_by_state[source_metadata.state],
                        input_count,
                        valid_count,
                        rejected_count,
                    )

                # Write valid chunk to Parquet
                if valid_count > 0:
                    table = pa.Table.from_pandas(
                        valid_chunk.reset_index(drop=True), preserve_index=False
                    )
                    if clean_writer is None:
                        clean_writer = pq.ParquetWriter(
                            clean_path, table.schema, compression='snappy'
                        )
                    else:
                        table = _ensure_schema_compatible(table, clean_writer, "clean")
                    clean_writer.write_table(table)

                # Write rejected chunk to Parquet
                if rejected_count > 0:
                    table = pa.Table.from_pandas(
                        rejected_chunk.reset_index(drop=True), preserve_index=False
                    )
                    if rejected_writer is None:
                        rejected_writer = pq.ParquetWriter(
                            rejected_path, table.schema, compression='snappy'
                        )
                    else:
                        table = _ensure_schema_compatible(
                            table, rejected_writer, "rejected"
                        )
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
       f.write("\nCounts by source file:\n")
       for file_name in sorted(counts_by_source_file):
           counts = counts_by_source_file[file_name]
           f.write(
               f"  {file_name}: total={counts['total_rows']}, "
               f"valid={counts['valid_rows']}, rejected={counts['rejected_rows']}\n"
           )
       f.write("\nCounts by year:\n")
       for year in sorted(counts_by_year):
           counts = counts_by_year[year]
           f.write(
               f"  {year}: total={counts['total_rows']}, "
               f"valid={counts['valid_rows']}, rejected={counts['rejected_rows']}\n"
           )
       f.write("\nCounts by state:\n")
       for state in sorted(counts_by_state):
           counts = counts_by_state[state]
           f.write(
               f"  {state}: total={counts['total_rows']}, "
               f"valid={counts['valid_rows']}, rejected={counts['rejected_rows']}\n"
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
        'failed_action_taken': reason_counts['invalid_action_taken'],
        'counts_by_source_file': dict(counts_by_source_file),
        'counts_by_year': dict(counts_by_year),
        'counts_by_state': dict(counts_by_state)
    }


if __name__ == "__main__":
    # Default paths
    input_path = config.RAW_DATA_DIR
    output_dir = config.PROCESSED_DATA_DIR

    # Run the ETL
    result = etl_hmda(input_path, output_dir, chunksize=config.CHUNK_SIZE)

    # Print summary
    print("HMDA ETL completed successfully.")
    print(f"Total rows processed: {result['total_rows_processed']}")
    print(f"Valid rows: {result['valid_rows']}")
    print(f"Rejected rows: {result['rejected_rows']}")
    print(f"Reconciliation difference: {result['reconciliation_difference']}")
