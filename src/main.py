"""
Main ETL pipeline for HMDA data.
"""

import pandas as pd
import logging
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any

from . import config, ingest, clean, transform, validate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.PROCESSED_DATA_DIR / "etl.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def process_chunk(chunk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Process a single chunk of data: clean, transform, validate.

    Returns
    -------
    valid_df : pd.DataFrame
        Valid rows from the chunk.
    rejected_df : pd.DataFrame
        Rejected rows from the chunk with rejection reasons.
    stats : dict
        Statistics for this chunk.
    """
    logger.debug(f"Processing chunk with {len(chunk)} rows.")

    # Step 1: Clean
    cleaned_df = clean.clean_dataframe(chunk)

    # Step 2: Transform (decode coded fields)
    transformed_df = transform.decode_categorical_fields(cleaned_df)

    # Step 3: Validate
    valid_df, rejected_df, stats = validate.validate_dataframe(transformed_df)

    return valid_df, rejected_df, stats

def run_etl() -> None:
    """
    Execute the full ETL pipeline.
    """
    logger.info("Starting HMDA ETL pipeline.")

    # Check if input file exists
    if not config.INPUT_FILE_PATH.exists():
        logger.error(f"Input file not found: {config.INPUT_FILE_PATH}")
        raise FileNotFoundError(f"Input file not found: {config.INPUT_FILE_PATH}")

    # Initialize accumulators
    all_valid_chunks: list[pd.DataFrame] = []
    all_rejected_chunks: list[pd.DataFrame] = []
    total_stats: dict = {
        'total_rows': 0,
        'valid_rows': 0,
        'rejected_rows': 0,
        'chunk_stats': []
    }

    # Process the file in chunks
    chunk_reader = ingest.read_hmda_csv(
        file_path=config.INPUT_FILE_PATH,
        chunk_size=config.CHUNK_SIZE
    )

    for chunk_num, chunk in enumerate(chunk_reader, start=1):
        logger.info(f"Processing chunk {chunk_num}.")

        try:
            valid_df, rejected_df, chunk_stats = process_chunk(chunk)

            # Append to accumulators
            all_valid_chunks.append(valid_df)
            all_rejected_chunks.append(rejected_df)

            # Update overall stats
            total_stats['total_rows'] += len(chunk)
            total_stats['valid_rows'] += len(valid_df)
            total_stats['rejected_rows'] += len(rejected_df)
            total_stats['chunk_stats'].append(chunk_stats)

            logger.info(
                f"Chunk {chunk_num}: {len(chunk)} rows processed, "
                f"{len(valid_df)} valid, {len(rejected_df)} rejected."
            )
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_num}: {e}", exc_info=True)
            # We could decide to skip the chunk or stop. For now, we'll raise.
            raise

    # Combine all chunks
    if all_valid_chunks:
        final_valid_df = pd.concat(all_valid_chunks, ignore_index=True)
    else:
        final_valid_df = pd.DataFrame()

    if all_rejected_chunks:
        final_rejected_df = pd.concat(all_rejected_chunks, ignore_index=True)
    else:
        final_rejected_df = pd.DataFrame()

    # Write output files
    logger.info(f"Writing {len(final_valid_df)} valid records to {config.CLEANED_FILE_PATH}")
    if not final_valid_df.empty:
        final_valid_df.to_parquet(
            config.CLEANED_FILE_PATH,
            index=False
        )

    logger.info(f"Writing {len(final_rejected_df)} rejected records to {config.REJECTED_FILE_PATH}")
    if not final_rejected_df.empty:
        final_rejected_df.to_parquet(
            config.REJECTED_FILE_PATH,
            index=False
        )

    # Write a summary report
    report_path = config.REPORT_FILE_PATH
    with open(report_path, 'w') as f:
        f.write("HMDA ETL Pipeline Summary\n")
        f.write("="*50 + "\n")
        f.write(f"Input file: {config.INPUT_FILE_PATH}\n")
        f.write(f"Total rows read: {total_stats['total_rows']}\n")
        f.write(f"Valid rows: {total_stats['valid_rows']}\n")
        f.write(f"Rejected rows: {total_stats['rejected_rows']}\n")
        f.write("\n")
        f.write("Per-chunk statistics:\n")
        for i, stats in enumerate(total_stats['chunk_stats'], start=1):
            f.write(f"  Chunk {i}: {stats}\n")

    logger.info(f"ETL pipeline completed. Report written to {report_path}")

    # Print summary to console
    print("\n=== ETL Summary ===")
    print(f"Input file: {config.INPUT_FILE_PATH}")
    print(f"Total rows read: {total_stats['total_rows']}")
    print(f"Valid rows: {total_stats['valid_rows']}")
    print(f"Rejected rows: {total_stats['rejected_rows']}")
    print(f"Valid data saved to: {config.CLEANED_FILE_PATH}")
    print(f"Rejected data saved to: {config.REJECTED_FILE_PATH}")
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    try:
        run_etl()
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        sys.exit(1)