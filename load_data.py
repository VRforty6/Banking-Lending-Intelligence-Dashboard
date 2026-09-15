#!/usr/bin/env python3
"""
Load the cleaned HMDA Parquet file into PostgreSQL staging table,
then populate the dimensional model.

This script performs the following steps:
1. Load environment variables for database connection.
2. Create a SQLAlchemy engine and test the connection.
3. Ensure schemas and tables exist (by executing SQL scripts).
4. Truncate the staging table for a fresh load.
5. Read the Parquet file in batches and load into staging.hmda_raw,
   adding stg_row_id, load_timestamp, and profile_hash columns.
6. Populate dimension tables from staging data.
7. Populate the fact table by joining staging with dimensions.
8. Create indexes on the fact table for performance.
9. Optionally create analytical views.
10. Run validation queries and log results.
"""

import os
import sys
import hashlib
import logging
import csv
from io import StringIO
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple

import pandas as pd
from sqlalchemy import create_engine, text, exc
from sqlalchemy.engine import Engine, URL

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent

SCHEMAS_SQL = PROJECT_ROOT / "sql" / "02_create_schemas.sql"
TABLES_SQL = PROJECT_ROOT / "sql" / "03_create_tables.sql"
VIEWS_SQL = PROJECT_ROOT / "sql" / "05_create_views.sql"
VALIDATION_SQL = PROJECT_ROOT / "sql" / "06_validation_queries.sql"

PARQUET_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "hmda_clean.parquet"
)

LOG_DIR = PROJECT_ROOT / "logs"

# The directory must exist before FileHandler is created
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / "load_data.log",
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)

STAGING_COPY_COLUMNS = [
    'stg_row_id',
    'load_timestamp',
    'activity_year',
    'lei',
    'derived_msa_md',
    'state_code',
    'county_code',
    'census_tract',
    'conforming_loan_limit',
    'derived_loan_product_type',
    'derived_dwelling_category',
    'derived_ethnicity',
    'derived_race',
    'derived_sex',
    'action_taken',
    'purchaser_type',
    'preapproval',
    'loan_type',
    'loan_purpose',
    'lien_status',
    'reverse_mortgage',
    'open_end_line_of_credit',
    'business_or_commercial_purpose',
    'loan_amount',
    'loan_to_value_ratio',
    'interest_rate',
    'rate_spread',
    'hoepa_status',
    'total_loan_costs',
    'total_points_and_fees',
    'origination_charges',
    'discount_points',
    'lender_credits',
    'loan_term',
    'prepayment_penalty_term',
    'intro_rate_period',
    'negative_amortization',
    'interest_only_payment',
    'balloon_payment',
    'other_nonamortizing_features',
    'property_value',
    'construction_method',
    'occupancy_type',
    'manufactured_home_secured_property_type',
    'manufactured_home_land_property_interest',
    'total_units',
    'multifamily_affordable_units',
    'income',
    'debt_to_income_ratio',
    'applicant_credit_score_type',
    'co_applicant_credit_score_type',
    'applicant_ethnicity_1',
    'applicant_ethnicity_2',
    'applicant_ethnicity_3',
    'applicant_ethnicity_4',
    'applicant_ethnicity_5',
    'co_applicant_ethnicity_1',
    'co_applicant_ethnicity_2',
    'co_applicant_ethnicity_3',
    'co_applicant_ethnicity_4',
    'co_applicant_ethnicity_5',
    'applicant_ethnicity_observed',
    'co_applicant_ethnicity_observed',
    'applicant_race_1',
    'applicant_race_2',
    'applicant_race_3',
    'applicant_race_4',
    'applicant_race_5',
    'co_applicant_race_1',
    'co_applicant_race_2',
    'co_applicant_race_3',
    'co_applicant_race_4',
    'co_applicant_race_5',
    'co_applicant_race_observed',
    'applicant_sex',
    'co_applicant_sex',
    'applicant_sex_observed',
    'co_applicant_sex_observed',
    'applicant_age',
    'co_applicant_age',
    'applicant_age_above_62',
    'co_applicant_age_above_62',
    'submission_of_application',
    'initially_payable_to_institution',
    'aus_1',
    'aus_2',
    'aus_3',
    'aus_4',
    'aus_5',
    'denial_reason_1',
    'denial_reason_2',
    'denial_reason_3',
    'denial_reason_4',
    'tract_population',
    'tract_minority_population_percent',
    'ffiec_msa_md_median_family_income',
    'tract_to_msa_income_percentage',
    'tract_owner_occupied_units',
    'tract_one_to_four_family_homes',
    'tract_median_age_of_housing_units',
    'profile_hash',
]
# Attempt to load python-dotenv if available
try:
    from dotenv import load_dotenv
    dotnet_available = True
except ImportError:
    dotnet_available = False

# Constants
SCHEMAS_SQL = PROJECT_ROOT / "sql" / "02_create_schemas.sql"
TABLES_SQL = PROJECT_ROOT / "sql" / "03_create_tables.sql"
VIEWS_SQL = PROJECT_ROOT / "sql" / "05_create_views.sql"
VALIDATION_SQL = PROJECT_ROOT / "sql" / "06_validation_queries.sql"
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "hmda_clean.parquet"

# Ensure log directory exists
LOG_DIR.mkdir(exist_ok=True)

def load_environment() -> Dict[str, str]:
    """Load environment variables for database connection."""
    if dotnet_available:
        load_dotenv(DOTENV_PATH := PROJECT_ROOT / '.env')
        if not DOTENV_PATH.exists():
            logger.warning(".env file not found, using system environment variables")

    required_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing environment variables: {', '.join(missing)}")

    return {
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT'),
        'database': os.getenv('POSTGRES_DB'),
        'username': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD')
    }

def get_db_connection_string(env: Dict[str, str]) -> URL:
    """Build SQLAlchemy connection string."""
    return URL.create(
        "postgresql+psycopg2",
        username=env['username'], password=env['password'],
        host=env['host'], port=int(env['port']), database=env['database'],
    )

def execute_sql_file(engine: Engine, filepath: Path) -> None:
    """Execute a SQL file, handling multiple statements and errors."""
    logger.info(f"Executing SQL file: {filepath}")
    try:
        with open(filepath, 'r') as f:
            sql_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL file not found: {filepath}")

    # Split by semicolon, but ignore semicolons within comments or strings?
    # For simplicity, we split on semicolon followed by newline and whitespace,
    # but this is not perfect. We assume the SQL files are formatted with
    # each statement ending with a semicolon on its own line.
    statements = [
        stmt.strip() for stmt in sql_content.split(';')
        if stmt.strip()
    ]

    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception as e:
                logger.error(f"Failed to execute statement: {statement[:200]}...")
                raise e
    logger.info(f"Successfully executed {filepath}")

def table_exists(engine: Engine, schema: str, table_name: str) -> bool:
    """Check if a table exists in the given schema."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema
                AND table_name = :table_name
            );
        """), {"schema": schema, "table_name": table_name})
        return result.scalar()

def ensure_tables_exist(engine: Engine) -> None:
    """Ensure that the required tables exist, creating them if necessary."""
    # First, ensure schemas exist (the SQL file already does this with IF NOT EXISTS)
    execute_sql_file(engine, SCHEMAS_SQL)

    # Now, for each table, check existence and create if missing.
    # We'll read the TABLES_SQL file and extract CREATE TABLE statements.
    # This is a simplification; we assume each CREATE TABLE statement is
    # separated by a blank line or semicolon and starts with "CREATE TABLE".
    try:
        with open(TABLES_SQL, 'r') as f:
            sql_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Tables SQL file not found: {TABLES_SQL}")

    # Split into statements by semicolon and filter for CREATE TABLE
    statements = [
        stmt.strip() for stmt in sql_content.split(';')
        if stmt.strip() and stmt.strip().upper().startswith('CREATE TABLE')
    ]

    for stmt in statements:
        # Extract table name from the CREATE TABLE statement
        # This is a naive implementation; it assumes the table name is the
        # third token in the statement (after CREATE and TABLE).
        parts = stmt.split()
        if len(parts) < 3:
            continue
        table_name = parts[2].strip('";')
        # Remove schema prefix if present (e.g., "staging." or "analytics.")
        if '.' in table_name:
            table_name = table_name.split('.')[1]

        if not table_exists(engine, 'staging' if table_name.startswith('hmda_raw') else 'analytics', table_name):
            logger.info(f"Creating table: {table_name}")
            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {e}")
                raise
        else:
            logger.debug(f"Table {table_name} already exists, skipping creation.")

def get_parquet_batches(parquet_path: Path, batch_size: int = 50000):
    """Yield batches of data from a Parquet file."""
    import pyarrow.parquet as pq

    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {parquet_path}")

    pf = pq.ParquetFile(parquet_path)
    total_rows = pf.metadata.num_rows
    logger.info(f"Total rows in Parquet file: {total_rows}")

    for batch in pf.iter_batches(batch_size=batch_size):
        batch_df = batch.to_pandas()

        # Normalize source column names to canonical snake_case
        batch_df.columns = [
            str(column).strip().lower().replace("-", "_").replace(" ", "_")
            for column in batch_df.columns
        ]

        # Guard against duplicate names created by normalization
        if batch_df.columns.duplicated().any():
            duplicate_columns = (
                batch_df.columns[batch_df.columns.duplicated()]
                .unique()
                .tolist()
            )
            raise ValueError(
                f"Duplicate columns after normalization: {duplicate_columns}"
            )

        yield batch_df

def compute_profile_hash(df: pd.DataFrame, profile_columns: List[str]) -> pd.Series:
    """
    Compute SHA-256 hash of the concatenated profile columns.

    Null/NaN values are replaced with empty strings before hashing.
    """
    def hash_row(row):
        values = []
        for col in profile_columns:
            val = row[col]
            if pd.isna(val):
                val = ''
            else:
                val = str(val).strip()
            values.append(val)
        concatenated = '|'.join(values)
        return hashlib.sha256(encode_utf8(concatenated)).hexdigest()

    # We'll use apply for clarity; note that this may be slow for large DataFrames.
    # For better performance, we could use vectorized string operations.
    return df.apply(hash_row, axis=1)

def encode_utf8(s: str) -> bytes:
    """Encode string to UTF-8 bytes."""
    return s.encode('utf-8')

def _get_driver_connection(sqlalchemy_connection):
    """
    Return the underlying DBAPI connection from a SQLAlchemy connection.

    SQLAlchemy 2.x exposes this as driver_connection. Older versions expose a
    compatible object through .connection.
    """
    raw_connection = sqlalchemy_connection.connection
    if hasattr(raw_connection, "driver_connection"):
        return raw_connection.driver_connection
    return raw_connection.connection

def build_copy_buffer(batch_df: pd.DataFrame) -> StringIO:
    """Build an in-memory CSV buffer for PostgreSQL COPY."""
    missing_columns = [
        column for column in STAGING_COPY_COLUMNS if column not in batch_df.columns
    ]
    if missing_columns:
        raise ValueError(
            "Batch is missing staging column(s): "
            + ", ".join(missing_columns)
        )

    ordered_df = batch_df.loc[:, STAGING_COPY_COLUMNS]
    buffer = StringIO()
    ordered_df.to_csv(
        buffer,
        index=False,
        header=False,
        na_rep="\\N",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    buffer.seek(0)
    return buffer

def copy_batch_to_staging(sqlalchemy_connection, batch_df: pd.DataFrame) -> None:
    """COPY one prepared batch into staging.hmda_raw using psycopg2."""
    columns_sql = ", ".join(f'"{column}"' for column in STAGING_COPY_COLUMNS)
    copy_sql = f"""
        COPY staging.hmda_raw ({columns_sql})
        FROM STDIN WITH (FORMAT CSV, NULL '\\N', QUOTE '"', ESCAPE '"')
    """
    buffer = build_copy_buffer(batch_df)
    driver_connection = _get_driver_connection(sqlalchemy_connection)
    with driver_connection.cursor() as cursor:
        cursor.copy_expert(copy_sql, buffer)

def load_staging_data(engine: Engine, batch_size: int = 50000) -> Tuple[int, int]:
    """
    Load data from Parquet into staging.hmda_raw.

    Returns:
        Tuple of (total_rows_loaded, number_of_batches)
    """
    logger.info("Starting to load Parquet data into staging table.")

    # Define the applicant profile columns for hashing (must match the staging table)
    profile_columns = [
        'applicant_ethnicity_1', 'applicant_ethnicity_2', 'applicant_ethnicity_3',
        'applicant_ethnicity_4', 'applicant_ethnicity_5', 'applicant_ethnicity_observed',
        'co_applicant_ethnicity_1', 'co_applicant_ethnicity_2', 'co_applicant_ethnicity_3',
        'co_applicant_ethnicity_4', 'co_applicant_ethnicity_5', 'co_applicant_ethnicity_observed',
        'applicant_race_1', 'applicant_race_2', 'applicant_race_3', 'applicant_race_4',
        'applicant_race_5', 'co_applicant_race_1', 'co_applicant_race_2', 'co_applicant_race_3',
        'co_applicant_race_4', 'co_applicant_race_5', 'co_applicant_race_observed',
        'applicant_sex', 'co_applicant_sex', 'applicant_sex_observed', 'co_applicant_sex_observed',
        'applicant_age', 'co_applicant_age', 'applicant_age_above_62', 'co_applicant_age_above_62',
        'applicant_credit_score_type', 'co_applicant_credit_score_type'
    ]

    # Ensure the profile columns exist in the staging table (they should)
    # We'll trust the schema.

    total_loaded = 0
    batch_number = 0
    start_id = 1  # stg_row_id starts at 1

    # Inspect input before opening a write transaction. A failed batch rolls
    # back both the truncate and all earlier batches, preserving old staging.
    import pyarrow.parquet as pq
    parquet_file = pq.ParquetFile(PARQUET_PATH)
    if parquet_file.metadata.num_rows == 0:
        raise ValueError("Refusing to replace staging with an empty Parquet file")
    required_source_columns = set(STAGING_COPY_COLUMNS) - {
        'stg_row_id', 'load_timestamp', 'profile_hash'
    }
    normalized_columns = [
        str(column).strip().lower().replace("-", "_").replace(" ", "_")
        for column in parquet_file.schema_arrow.names
    ]
    if len(normalized_columns) != len(set(normalized_columns)):
        raise ValueError("Duplicate columns after normalization")
    missing_columns = required_source_columns - set(normalized_columns)
    if missing_columns:
        raise ValueError(f"Parquet is missing staging columns: {sorted(missing_columns)}")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE staging.hmda_raw RESTART IDENTITY"))

        for batch_df in get_parquet_batches(PARQUET_PATH, batch_size=batch_size):
            batch_number += 1
            batch_size_actual = len(batch_df)
            end_id = start_id + batch_size_actual - 1

            # Add staging columns
            batch_df = batch_df.copy()
            batch_df['stg_row_id'] = range(start_id, end_id + 1)
            batch_df['load_timestamp'] = datetime.now()

            # Compute profile hash
            batch_df['profile_hash'] = compute_profile_hash(batch_df, profile_columns)

            try:
                copy_batch_to_staging(conn, batch_df)
                total_loaded += batch_size_actual
                logger.info(
                    f"Loaded batch {batch_number} ({batch_size_actual} rows). "
                    f"Total loaded: {total_loaded}"
                )
            except Exception as e:
                logger.error(f"Failed to load batch {batch_number}: {e}")
                raise

            start_id = end_id + 1

    logger.info(f"Finished loading {total_loaded} rows in {batch_number} batches.")
    return total_loaded, batch_number

def populate_dimensions(engine: Engine) -> None:
    """Populate dimension tables from staging data."""
    logger.info("Starting to populate dimension tables.")

    # These SQL statements are adapted from the previous load_data.py script.
    # We use INSERT ... SELECT DISTINCT with ON CONFLICT DO NOTHING to avoid duplicates.

    dimension_scripts = [
        ("dim_lender", """
            INSERT INTO analytics.dim_lender (lei)
            SELECT DISTINCT lei
            FROM staging.hmda_raw
            WHERE lei IS NOT NULL
            ON CONFLICT (lei) DO NOTHING;
        """),
        ("dim_geography", """
            INSERT INTO analytics.dim_geography (
                state_code, county_code, census_tract, tract_population,
                tract_minority_population_percent, ffiec_msa_md_median_family_income,
                tract_to_msa_income_percentage, tract_owner_occupied_units,
                tract_one_to_four_family_homes, tract_median_age_of_housing_units
            )
            SELECT DISTINCT
                state_code,
                CASE
                    WHEN county_code IS NOT NULL THEN county_code
                    WHEN census_tract IS NOT NULL THEN LEFT(census_tract, 5)
                    ELSE 'UNKNOWN'
                END AS county_code,
                census_tract,
                CASE WHEN tract_population = '' THEN NULL ELSE tract_population::bigint END,
                CASE WHEN tract_minority_population_percent = '' THEN NULL ELSE tract_minority_population_percent::double precision END,
                CASE WHEN ffiec_msa_md_median_family_income = '' THEN NULL ELSE ffiec_msa_md_median_family_income::double precision END,
                CASE WHEN tract_to_msa_income_percentage = '' THEN NULL ELSE tract_to_msa_income_percentage::double precision END,
                CASE WHEN tract_owner_occupied_units = '' THEN NULL ELSE tract_owner_occupied_units::bigint END,
                CASE WHEN tract_one_to_four_family_homes = '' THEN NULL ELSE tract_one_to_four_family_homes::bigint END,
                CASE WHEN tract_median_age_of_housing_units = '' THEN NULL ELSE tract_median_age_of_housing_units::int END
            FROM staging.hmda_raw
            WHERE state_code IS NOT NULL
                AND (county_code IS NOT NULL OR census_tract IS NOT NULL)
                AND census_tract IS NOT NULL
            ON CONFLICT (state_code, county_code, census_tract) DO NOTHING;
		INSERT INTO analytics.dim_geography (
 			   state_code,
			    county_code,
 			   census_tract
			)
			SELECT DISTINCT
   			 state_code,
   			 COALESCE(county_code, 'UNKNOWN') AS county_code,
   			 'UNKNOWN' AS census_tract
			FROM staging.hmda_raw
			WHERE state_code IS NOT NULL
		        AND census_tract IS NULL
			ON CONFLICT (state_code, county_code, census_tract) DO NOTHING;
       			 """),
        ("dim_loan", """
            INSERT INTO analytics.dim_loan (
                loan_type, loan_purpose, lien_status, reverse_mortgage,
                open_end_line_of_credit, business_or_commercial_purpose,
                conforming_loan_limit
            )
            SELECT DISTINCT
                loan_type, loan_purpose, lien_status,
                reverse_mortgage, open_end_line_of_credit,
                business_or_commercial_purpose, conforming_loan_limit
            FROM staging.hmda_raw
            WHERE loan_type IS NOT NULL AND loan_purpose IS NOT NULL AND lien_status IS NOT NULL
            ON CONFLICT (loan_type, loan_purpose, lien_status, reverse_mortgage, open_end_line_of_credit, business_or_commercial_purpose, conforming_loan_limit) DO NOTHING;
        """),
        ("dim_applicant_profile", """
            INSERT INTO analytics.dim_applicant_profile (
                applicant_ethnicity_1, applicant_ethnicity_2, applicant_ethnicity_3, applicant_ethnicity_4, applicant_ethnicity_5,
                applicant_ethnicity_observed,
                co_applicant_ethnicity_1, co_applicant_ethnicity_2, co_applicant_ethnicity_3, co_applicant_ethnicity_4, co_applicant_ethnicity_5,
                co_applicant_ethnicity_observed,
                applicant_race_1, applicant_race_2, applicant_race_3, applicant_race_4, applicant_race_5,
                co_applicant_race_1, co_applicant_race_2, co_applicant_race_3, co_applicant_race_4, co_applicant_race_5,
                co_applicant_race_observed,
                applicant_sex, co_applicant_sex, applicant_sex_observed, co_applicant_sex_observed,
                applicant_age, co_applicant_age, applicant_age_above_62, co_applicant_age_above_62,
                applicant_credit_score_type, co_applicant_credit_score_type,
                profile_hash
            )
            SELECT
                applicant_ethnicity_1, applicant_ethnicity_2, applicant_ethnicity_3, applicant_ethnicity_4, applicant_ethnicity_5,
                applicant_ethnicity_observed,
                co_applicant_ethnicity_1, co_applicant_ethnicity_2, co_applicant_ethnicity_3, co_applicant_ethnicity_4, co_applicant_ethnicity_5,
                co_applicant_ethnicity_observed,
                applicant_race_1, applicant_race_2, applicant_race_3, applicant_race_4, applicant_race_5,
                co_applicant_race_1, co_applicant_race_2, co_applicant_race_3, co_applicant_race_4, co_applicant_race_5,
                co_applicant_race_observed,
                applicant_sex, co_applicant_sex, applicant_sex_observed, co_applicant_sex_observed,
                applicant_age, co_applicant_age, applicant_age_above_62, co_applicant_age_above_62,
                applicant_credit_score_type, co_applicant_credit_score_type,
                profile_hash
            FROM staging.hmda_raw
            ON CONFLICT (profile_hash) DO NOTHING;
        """),
        ("dim_action_taken", """
            INSERT INTO analytics.dim_action_taken (action_taken)
            SELECT DISTINCT action_taken
            FROM staging.hmda_raw
            WHERE action_taken IS NOT NULL
            ON CONFLICT (action_taken) DO NOTHING;
        """)
    ]

    for table_name, sql in dimension_scripts:
        logger.info(f"Populating dimension table: {table_name}")
        try:
            with engine.begin() as conn:
                conn.execute(text(sql))
            logger.info(f"Successfully populated {table_name}")
        except Exception as e:
            logger.error(f"Failed to populate {table_name}: {e}")
            raise

def populate_fact_table(engine: Engine) -> None:
    """Populate the fact table by joining staging with dimensions."""
    logger.info("Starting to populate fact table.")

    fact_sql = """
        TRUNCATE TABLE analytics.fact_loan_application RESTART IDENTITY;

        INSERT INTO analytics.fact_loan_application (
            lei_key, geography_key, loan_key, applicant_profile_key, action_taken_key,
            loan_amount, income, application_year, source_row_id, load_timestamp
        )
        SELECT
            l.lei_key,
            g.geography_key,
            ln.loan_key,
            a.applicant_profile_key,
            t.action_taken_key,
            s.loan_amount,
            s.income,
            s.activity_year,
            s.stg_row_id,
            s.load_timestamp
        FROM staging.hmda_raw s
        LEFT JOIN analytics.dim_lender l ON s.lei = l.lei
        LEFT JOIN (
            SELECT DISTINCT ON (state_code, county_code, census_tract) geography_key, state_code, county_code, census_tract
            FROM analytics.dim_geography
            ORDER BY state_code, county_code, census_tract
        ) g ON s.state_code = g.state_code
     AND g.county_code =
         CASE
             WHEN s.county_code IS NOT NULL THEN s.county_code
             WHEN s.census_tract IS NOT NULL THEN LEFT(s.census_tract, 5)
             ELSE 'UNKNOWN'
         END
     AND g.census_tract =
         CASE
             WHEN s.census_tract IS NOT NULL THEN s.census_tract
             ELSE 'UNKNOWN'
         END
        LEFT JOIN (
            SELECT DISTINCT ON (loan_type, loan_purpose, lien_status, reverse_mortgage, open_end_line_of_credit,
                                business_or_commercial_purpose, conforming_loan_limit)
                loan_key, loan_type, loan_purpose, lien_status,
                reverse_mortgage, open_end_line_of_credit, business_or_commercial_purpose, conforming_loan_limit
            FROM analytics.dim_loan
            ORDER BY loan_type, loan_purpose, lien_status,
                     reverse_mortgage, open_end_line_of_credit, business_or_commercial_purpose, conforming_loan_limit
       ) ln ON s.loan_type IS NOT DISTINCT FROM ln.loan_type
      AND s.loan_purpose IS NOT DISTINCT FROM ln.loan_purpose
      AND s.lien_status IS NOT DISTINCT FROM ln.lien_status
      AND s.reverse_mortgage IS NOT DISTINCT FROM ln.reverse_mortgage
      AND s.open_end_line_of_credit IS NOT DISTINCT FROM ln.open_end_line_of_credit
      AND s.business_or_commercial_purpose IS NOT DISTINCT FROM ln.business_or_commercial_purpose
      AND s.conforming_loan_limit IS NOT DISTINCT FROM ln.conforming_loan_limit
        LEFT JOIN (
            SELECT applicant_profile_key, profile_hash
            FROM analytics.dim_applicant_profile
        ) a ON s.profile_hash = a.profile_hash
        LEFT JOIN (
            SELECT DISTINCT action_taken, action_taken_key
            FROM analytics.dim_action_taken
        ) t ON s.action_taken = t.action_taken
        WHERE s.stg_row_id IS NOT NULL;
    """

    try:
        with engine.begin() as conn:
            conn.execute(text(fact_sql))
        logger.info("Successfully populated fact table.")
    except Exception as e:
        logger.error(f"Failed to populate fact table: {e}")
        raise

def create_indexes(engine: Engine) -> None:
    """Create indexes on the fact table for performance."""
    logger.info("Creating indexes on fact table.")

    index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_fact_lei ON analytics.fact_loan_application(lei_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_geography ON analytics.fact_loan_application(geography_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_loan ON analytics.fact_loan_application(loan_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_applicant ON analytics.fact_loan_application(applicant_profile_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_action ON analytics.fact_loan_application(action_taken_key);",
        "CREATE INDEX IF NOT EXISTS idx_fact_year ON analytics.fact_loan_application(application_year);"
    ]

    with engine.begin() as conn:
        for stmt in index_statements:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.error(f"Failed to create index: {stmt}")
                raise
    logger.info("Indexes created.")

def create_views(engine: Engine) -> None:
    """Create analytical views."""
    logger.info("Creating views.")
    execute_sql_file(engine, VIEWS_SQL)

def is_result_returning_validation_statement(statement: str) -> bool:
    """Return True when a validation statement should be fetched and logged."""
    normalized = statement.strip().upper()
    return normalized.startswith("SELECT") or normalized.startswith("WITH")

def run_validations(engine: Engine) -> None:
    """Run validation queries and log results."""
    logger.info("Running validation queries.")

    try:
        with open(VALIDATION_SQL, 'r') as f:
            sql_content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Validation SQL file not found: {VALIDATION_SQL}")

    # Split by semicolon and execute each statement
    statements = [
        stmt.strip() for stmt in sql_content.split(';')
        if stmt.strip()
    ]

    failed_checks = []
    check_count = 0
    with engine.connect() as conn:
        for statement in statements:
            if not statement:
                continue
            try:
                result = conn.execute(text(statement))
                # For SELECT statements, we can fetch and log the results
                if is_result_returning_validation_statement(statement):
                    rows = result.fetchall()
                    # Log the query and results
                    logger.info(f"Validation query: {statement}")
                    for row in rows:
                        logger.info(f"  Result: {row}")
                        check_count += 1
                        if row._mapping['status'] != 'PASS':
                            failed_checks.append(str(row._mapping['check']))
                else:
                    # For non-SELECT, just log that it executed
                    logger.info(f"Validation statement executed: {statement[:100]}...")
            except Exception as e:
                logger.error(f"Failed to execute validation query: {statement[:200]}...")
                raise e
    if not check_count:
        raise RuntimeError("Warehouse validation returned no checks")
    if failed_checks:
        raise RuntimeError("Warehouse validation failed: " + ", ".join(failed_checks))
    logger.info("Validation queries completed: all checks passed.")

def main() -> None:
    """Main ETL orchestration function."""
    logger.info("Starting HMDA ETL pipeline (load_data.py).")

    # Initialize engine
    engine = None
    try:
        # Step 1: Load environment
        env = load_environment()
        logger.info(f"Connecting to database at {env['host']}:{env['port']}/{env['database']}")

        # Step 2: Create database connection
        connection_string = get_db_connection_string(env)
        engine = create_engine(connection_string)

        if sys.argv[1:] and sys.argv[1:] != ['--validate-only']:
            raise ValueError("Usage: python load_data.py [--validate-only]")
        if sys.argv[1:] == ['--validate-only']:
            run_validations(engine)
            return

        # Step 3: Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.scalar()
            logger.info(f"Connected to PostgreSQL: {version}")

        # Step 4: Ensure schemas and tables exist
        ensure_tables_exist(engine)

        # Step 5: Load staging data
        total_rows, batch_count = load_staging_data(engine)
        logger.info(f"Staging load complete: {total_rows} rows in {batch_count} batches.")

        # Step 6: Populate dimensions
        populate_dimensions(engine)

        # Step 7: Populate fact table
        populate_fact_table(engine)

        # Step 8: Create indexes
        create_indexes(engine)

        # Step 9: Create views (optional)
        create_views(engine)

        # Step 10: Run validations
        run_validations(engine)

        logger.info("ETL pipeline completed successfully.")

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        if engine is not None:
            engine.dispose()
            logger.info("Database connection disposed.")

if __name__ == "__main__":
    main()
