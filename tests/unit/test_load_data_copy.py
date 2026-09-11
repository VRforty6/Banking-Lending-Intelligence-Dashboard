import csv
from io import StringIO
from types import SimpleNamespace

import pandas as pd

from load_data import STAGING_COPY_COLUMNS, copy_batch_to_staging, populate_dimensions


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
