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


class ValidationConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement):
        return SimpleNamespace(fetchall=lambda: self.rows)


def validation_engine(statuses):
    rows = [SimpleNamespace(_mapping={'check': name, 'status': status})
            for name, status in statuses]
    return SimpleNamespace(connect=lambda: ValidationConnection(rows))


def test_validation_failure_stops_loader():
    import pytest
    from load_data import run_validations

    with pytest.raises(RuntimeError, match='Missing mappings'):
        run_validations(validation_engine([('Counts', 'PASS'), ('Missing mappings', 'FAIL')]))


def test_validation_success_and_empty_results():
    import pytest
    from load_data import run_validations

    run_validations(validation_engine([('Counts', 'PASS')]))
    with pytest.raises(RuntimeError, match='no checks'):
        run_validations(validation_engine([]))


def test_connection_url_preserves_special_characters():
    from load_data import get_db_connection_string

    url = get_db_connection_string(dict(username='user', password='p@ss:/?#%',
                                        host='localhost', port='5432', database='hmda'))
    assert url.password == 'p@ss:/?#%'
    assert url.host == 'localhost'
    assert url.database == 'hmda'


class TransactionEngine:
    """Model transaction commit/rollback to inspect the loader boundary."""
    def __init__(self):
        self.current = ['old staging']
        self.begins = 0

    def begin(self):
        self.begins += 1
        engine = self

        class Transaction:
            def __enter__(self):
                self.pending = list(engine.current)
                return self

            def execute(self, statement):
                self.pending.clear()

            def __exit__(self, exc_type, exc, traceback):
                if exc_type is None:
                    engine.current = self.pending
                return False

        return Transaction()


def write_staging_fixture(path, rows=2):
    import pyarrow as pa
    import pyarrow.parquet as pq
    columns = set(STAGING_COPY_COLUMNS) - {'stg_row_id', 'load_timestamp', 'profile_hash'}
    pq.write_table(pa.Table.from_pydict({column: ['1'] * rows for column in columns}), path)


def test_missing_or_empty_parquet_does_not_touch_staging(tmp_path, monkeypatch):
    import pytest
    import load_data

    path = tmp_path / 'input.parquet'
    monkeypatch.setattr(load_data, 'PARQUET_PATH', path)
    engine = TransactionEngine()
    with pytest.raises(FileNotFoundError):
        load_data.load_staging_data(engine)
    write_staging_fixture(path, rows=0)
    with pytest.raises(ValueError, match='empty Parquet'):
        load_data.load_staging_data(engine)
    assert engine.begins == 0
    assert engine.current == ['old staging']


def test_failed_second_batch_rolls_back_entire_staging_load(tmp_path, monkeypatch):
    import pytest
    import load_data

    path = tmp_path / 'input.parquet'
    write_staging_fixture(path)
    monkeypatch.setattr(load_data, 'PARQUET_PATH', path)
    engine = TransactionEngine()
    calls = []

    def copy(connection, batch):
        calls.append(batch['stg_row_id'].tolist())
        connection.pending.extend(batch['stg_row_id'].tolist())
        if len(calls) == 2:
            raise RuntimeError('simulated COPY failure')

    monkeypatch.setattr(load_data, 'copy_batch_to_staging', copy)
    with pytest.raises(RuntimeError, match='simulated COPY failure'):
        load_data.load_staging_data(engine, batch_size=1)
    assert calls == [[1], [2]]
    assert engine.begins == 1
    assert engine.current == ['old staging']


def test_successful_staging_load_commits_all_batches(tmp_path, monkeypatch):
    import load_data

    path = tmp_path / 'input.parquet'
    write_staging_fixture(path)
    monkeypatch.setattr(load_data, 'PARQUET_PATH', path)
    engine = TransactionEngine()
    monkeypatch.setattr(load_data, 'copy_batch_to_staging',
                        lambda connection, batch: connection.pending.extend(batch['stg_row_id'].tolist()))
    assert load_data.load_staging_data(engine, batch_size=1) == (2, 2)
    assert engine.current == [1, 2]
    assert engine.begins == 1
