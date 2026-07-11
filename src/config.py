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

# Input file name
INPUT_FILE_NAME = "state_CA.csv"
INPUT_FILE_PATH = RAW_DATA_DIR / INPUT_FILE_NAME

# Output file names (we'll write in Parquet for efficiency, but also CSV if needed)
# We'll output cleaned data as Parquet
CLEANED_FILE_NAME = "cleaned_data.parquet"
CLEANED_FILE_PATH = PROCESSED_DATA_DIR / CLEANED_FILE_NAME

REJECTED_FILE_NAME = "rejected_data.parquet"
REJECTED_FILE_PATH = PROCESSED_DATA_DIR / REJECTED_FILE_NAME

# We'll also output a summary report
REPORT_FILE_NAME = "validation_report.txt"
REPORT_FILE_PATH = PROCESSED_DATA_DIR / REPORT_FILE_NAME

# HMDA specific constants
HMDA_NA_STRING = "NA"  # string used for missing values in the raw data

# Valid years for activity_year (can be extended)
VALID_YEARS = {2025}

# Batch size for chunked reading (if we decide to chunk)
CHUNK_SIZE = 100_000  # rows per chunk

# Configure logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"