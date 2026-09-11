import csv
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from load_data import (
    STAGING_COPY_COLUMNS,
    copy_batch_to_staging,
    is_result_returning_validation_statement,
    populate_dimensions,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_SQL = PROJECT_ROOT / "sql" / "06_validation_queries.sql"


class FakeCursor:
    def __init__(self):
        self.copy_sql = None
        self.copy_data = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def copy_expert(self, sql, file_obj):
        self.copy_sql = sql
        self.copy_data = file_obj.read()


class FakeDriverConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()

    def cursor(self):
        return self.cursor_obj


def test_copy_batch_to_staging_uses_copy_with_ordered_columns_and_nulls():
    """COPY helper emits staging-ordered CSV with deterministic empty-field NULLs."""
    row = {column: f"value_{column}" for column in STAGING_COPY_COLUMNS}
    row.update(
        {
            "stg_row_id": 1,
            "load_timestamp": "2026-09-11 12:34:56",
            "activity_year": 2024,
            "state_code": "TX",
            "loan_amount": 250000.0,
            "income": pd.NA,
            "profile_hash": "a" * 64,
        }
    )
    batch_df = pd.DataFrame([row])

    driver_connection = FakeDriverConnection()
    sqlalchemy_connection = SimpleNamespace(
        connection=SimpleNamespace(driver_connection=driver_connection)
    )

    copy_batch_to_staging(sqlalchemy_connection, batch_df)

    cursor = driver_connection.cursor_obj
    assert "COPY staging.hmda_raw" in cursor.copy_sql
    assert '"stg_row_id", "load_timestamp", "activity_year"' in cursor.copy_sql
    assert "FROM STDIN WITH (FORMAT CSV, NULL '\\N'" in cursor.copy_sql

    parsed_rows = list(csv.reader(StringIO(cursor.copy_data)))
    assert len(parsed_rows) == 1

    copied_row = parsed_rows[0]
    assert len(copied_row) == len(STAGING_COPY_COLUMNS)
    assert copied_row[STAGING_COPY_COLUMNS.index("stg_row_id")] == "1"
    assert copied_row[STAGING_COPY_COLUMNS.index("activity_year")] == "2024"
    assert copied_row[STAGING_COPY_COLUMNS.index("state_code")] == "TX"
    assert copied_row[STAGING_COPY_COLUMNS.index("loan_amount")] == "250000.0"
    assert copied_row[STAGING_COPY_COLUMNS.index("income")] == "\\N"
    assert copied_row[STAGING_COPY_COLUMNS.index("profile_hash")] == "a" * 64


class FakeSqlConnection:
    def __init__(self, statements):
        self.statements = statements

    def execute(self, statement):
        self.statements.append(str(statement))


class FakeEngineBegin:
    def __init__(self, statements):
        self.statements = statements

    def __enter__(self):
        return FakeSqlConnection(self.statements)

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    def __init__(self):
        self.statements = []

    def begin(self):
        return FakeEngineBegin(self.statements)


def test_dim_geography_derives_missing_county_from_census_tract():
    """Geography dimension matches fact county fallback for null county codes."""
    engine = FakeEngine()

    populate_dimensions(engine)

    geography_sql = next(
        statement
        for statement in engine.statements
        if "INSERT INTO analytics.dim_geography" in statement
    )
    assert "WHEN census_tract IS NOT NULL THEN LEFT(census_tract, 5)" in geography_sql
    assert "END AS county_code" in geography_sql
    assert "county_code IS NOT NULL OR census_tract IS NOT NULL" in geography_sql

    row = {
        "state_code": "TX",
        "county_code": None,
        "census_tract": "48113007206",
    }
    canonical_county_code = (
        row["county_code"]
        if row["county_code"] is not None
        else row["census_tract"][:5]
        if row["census_tract"] is not None
        else "UNKNOWN"
    )

    assert canonical_county_code == "48113"


def test_validation_sql_uses_dynamic_staging_fact_row_counts():
    """Validation row counts compare current staging and fact counts."""
    sql = VALIDATION_SQL.read_text(encoding="utf-8")

    assert "1161292" not in sql
    assert "warehouse_counts AS" in sql
    assert "(SELECT COUNT(*) FROM staging.hmda_raw) AS staging_count" in sql
    assert (
        "(SELECT COUNT(*) FROM analytics.fact_loan_application) AS fact_count"
        in sql
    )
    assert "CASE WHEN staging_count = fact_count THEN 'PASS'" in sql
    assert "CASE WHEN fact_count = staging_count THEN 'PASS'" in sql


def test_validation_sql_duplicate_check_returns_zero_without_duplicates():
    """Duplicate source-row validation cannot return NULL for empty results."""
    sql = VALIDATION_SQL.read_text(encoding="utf-8")

    assert "duplicate_source_rows AS" in sql
    assert "COALESCE(SUM(row_count), 0)::bigint AS duplicate_count" in sql
    assert "duplicate_count AS actual_count" in sql
    assert "CASE WHEN duplicate_count = 0 THEN 'PASS'" in sql


def test_validation_runner_fetches_with_query_results():
    """Dynamic validation CTEs are logged as result-returning checks."""
    assert is_result_returning_validation_statement("SELECT 1")
    assert is_result_returning_validation_statement("  WITH counts AS (SELECT 1)")
    assert not is_result_returning_validation_statement("CREATE INDEX example")
