"""
Ingest module for reading HMDA CSV file in chunks.
"""

import pandas as pd
from pathlib import Path
import logging

from . import config

logger = logging.getLogger(__name__)

def read_hmda_csv(file_path: Path = None, chunk_size: int = None):
    """
    Read the HMDA CSV file in chunks.

    Parameters
    ----------
    file_path : Path, optional
        Path to the CSV file. If None, uses config.INPUT_FILE.
    chunk_size : int, optional
        Number of rows per chunk. If None, uses config.CHUNK_SIZE.

    Yields
    ------
    pandas.DataFrame
        A chunk of data as a DataFrame.
    """
    if file_path is None:
        file_path = config.INPUT_FILE
    if chunk_size is None:
        chunk_size = config.CHUNK_SIZE

    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    logger.info(f"Reading CSV file {file_path} in chunks of {chunk_size} rows.")

    # We'll read the file with all columns as string initially to avoid dtype issues.
    # We'll also specify the NA strings to be converted to NaN later.
    # However, we want to keep 'NA' as a string to handle it in cleaning step?
    # Actually, we want to convert 'NA' to NaN for numeric columns, but keep as string for categorical?
    # Let's read everything as object (string) and then convert in cleaning.
    # We'll also set low_memory=False to avoid mixed type inference.

    # Use chunk iterator
    chunk_iterator = pd.read_csv(
        file_path,
        sep=',',
        header=0,
        dtype=str,  # read all columns as string
        na_values=[],
        keep_default_na=False,  # we will handle 'NA' ourselves
        chunksize=chunk_size,
        iterator=True
    )

    for chunk in chunk_iterator:
        # Strip whitespace from column names (if any)
        chunk.columns = [col.strip() for col in chunk.columns]
        yield chunk

    logger.info("Finished reading all chunks.")