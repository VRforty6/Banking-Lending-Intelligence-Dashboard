"""
Configuration module for the ETL pipeline.
"""

from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
LOOKUP_DATA_DIR = RAW_DATA_DIR / "lookup"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOOKUP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Raw HMDA files are discovered from data/raw using this convention:
# hmda_<YEAR>_<STATE>.csv, for example hmda_2025_CA.csv.
RAW_FILE_PATTERN = "hmda_*_*.csv"

# Output file names used by the production pipeline and load_data.py.
CLEANED_FILE_NAME = "hmda_clean.parquet"
CLEANED_FILE_PATH = PROCESSED_DATA_DIR / CLEANED_FILE_NAME

REJECTED_FILE_NAME = "hmda_rejected.parquet"
REJECTED_FILE_PATH = PROCESSED_DATA_DIR / REJECTED_FILE_NAME

# We'll also output a summary report
REPORT_FILE_NAME = "validation_report.txt"
REPORT_FILE_PATH = PROCESSED_DATA_DIR / REPORT_FILE_NAME

# HMDA specific constants
HMDA_NA_STRING = "NA"  # string used for missing values in the raw data

# Supported HMDA extracts for the current ingestion scope.
SUPPORTED_STATES = {"CA", "TX", "FL", "NY", "IL"}
VALID_YEARS = {2023, 2024, 2025}

# Batch size for chunked reading (if we decide to chunk)
CHUNK_SIZE = 100_000  # rows per chunk

# Configure logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
