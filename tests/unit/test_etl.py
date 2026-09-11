import os

import pandas as pd
import pytest

from etl_hmda import (
    clean_chunk,
    discover_hmda_files,
    etl_hmda,
    validate_chunk,
)


NA_VALUES = ["", "NA", "N/A", "Exempt", "nan", "<NA>"]


def test_numeric_conversion(tmp_path):
    """Convert required fields without corrupting LEI identifiers."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
2021,2,200000,60000,23456789012345
,3,300000,70000,34567890123456
2022,4,,80000,45678901234567
2023,5,500000,,56789012345678
2024,6,0,90000,67890123456789
2025,7,-100,100000,78901234567890
2026,8,100000,110000,
2027,9,100000,120000,NA
2028,10,100000,130000,N/A
2029,11,100000,140000,nan
2030,12,100000,150000,<NA>
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    df = pd.read_csv(
        csv_path,
        keep_default_na=True,
        na_values=NA_VALUES,
        dtype={"lei": "string"},
    )
    cleaned = clean_chunk(df)

    assert cleaned["activity_year"].dtype == "Int64"
    assert cleaned["action_taken"].dtype == "Int64"
    assert pd.api.types.is_float_dtype(cleaned["loan_amount"])
    assert pd.api.types.is_float_dtype(cleaned["income"])
    assert cleaned["lei"].dtype == "string"

    assert cleaned.loc[0, "activity_year"] == 2020
    assert cleaned.loc[0, "action_taken"] == 1
    assert cleaned.loc[0, "loan_amount"] == 100000.0
    assert cleaned.loc[0, "income"] == 50000.0
    assert cleaned.loc[0, "lei"] == "12345678901234"

    assert pd.isna(cleaned.loc[2, "activity_year"])
    assert pd.isna(cleaned.loc[3, "loan_amount"])
    assert pd.isna(cleaned.loc[4, "income"])

    assert cleaned.loc[5, "loan_amount"] == 0.0
    assert cleaned.loc[6, "loan_amount"] == -100.0

    for row_index in range(7, 12):
        assert pd.isna(cleaned.loc[row_index, "lei"])


def test_action_taken_validation():
    """Accept only non-null action_taken values from 1 through 8."""
    df = pd.DataFrame(
        {
            "activity_year": [2020] * 6,
            "action_taken": [1, 5, 9, 0, None, 2],
            "loan_amount": [100000.0] * 6,
            "income": [50000.0] * 6,
            "lei": ["12345678901234"] * 6,
        }
    )

    valid, rejected, counts = validate_chunk(clean_chunk(df))

    assert len(valid) == 3
    assert len(rejected) == 3
    assert counts["invalid_action_taken"] == 3
    assert rejected["rejection_reason"].str.contains(
        "invalid_action_taken", regex=False
    ).all()


def test_row_retention_and_rejection():
    """Keep valid rows and reject one row for each documented rule."""
    df = pd.DataFrame(
        {
            "activity_year": [None, 2020, 2020, 2020, 2020],
            "lei": [
                "12345678901234",
                None,
                "12345678901234",
                "12345678901234",
                "12345678901234",
            ],
            "action_taken": [1, 1, 9, 1, 1],
            "loan_amount": [100000.0, 100000.0, 100000.0, -5000.0, 100000.0],
            "income": [50000.0] * 5,
        }
    )

    valid, rejected, counts = validate_chunk(clean_chunk(df))

    assert len(valid) == 1
    assert len(rejected) == 4
    assert counts == {
        "missing_activity_year": 1,
        "missing_lei": 1,
        "invalid_action_taken": 1,
        "invalid_loan_amount": 1,
    }
    assert set(rejected["rejection_reason"]) == {
        "missing_activity_year",
        "missing_lei",
        "invalid_action_taken",
        "invalid_loan_amount",
    }


def test_multiple_rejection_reasons():
    """Attach every applicable rejection reason in deterministic order."""
    df = pd.DataFrame(
        {
            "activity_year": [None, None, 2020, 2020],
            "lei": [None, "12345678901234", None, "12345678901234"],
            "action_taken": [1, 9, 1, 9],
            "loan_amount": [100000.0, 100000.0, -5000.0, 100000.0],
            "income": [50000.0] * 4,
        }
    )

    valid, rejected, counts = validate_chunk(clean_chunk(df))

    assert len(valid) == 0
    assert len(rejected) == 4
    assert counts == {
        "missing_activity_year": 2,
        "missing_lei": 2,
        "invalid_action_taken": 2,
        "invalid_loan_amount": 1,
    }

    assert rejected["rejection_reason"].tolist() == [
        "missing_activity_year;missing_lei",
        "missing_activity_year;invalid_action_taken",
        "missing_lei;invalid_loan_amount",
        "invalid_action_taken",
    ]


def test_validation_report(tmp_path):
    """Write an exact, line-oriented validation report."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
2020,2,200000,60000,23456789012345
2020,3,,70000,34567890123456
2020,4,400000,,56789012345678
2020,5,0,90000,67890123456789
2020,6,-100,100000,78901234567890
2020,7,100000,110000,
2020,8,100000,120000,NA
"""
    input_path = tmp_path / "input.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(csv_text, encoding="utf-8")

    result = etl_hmda(input_path, output_dir, chunksize=3)
    report_path = output_dir / "validation_report.txt"

    assert report_path.exists()
    lines = report_path.read_text(encoding="utf-8").splitlines()

    assert lines == [
        "HMDA ETL Validation Report",
        "Total rows processed: 8",
        "Valid rows: 4",
        "Rejected rows: 4",
        "Reconciliation difference: 0",
        "Failed activity_year (missing): 0",
        "Failed lei (missing): 2",
        "Failed loan_amount (invalid): 2",
        "Failed action_taken (invalid): 0",
        "",
        "Counts by source file:",
        "  input.csv: total=8, valid=4, rejected=4",
        "",
        "Counts by year:",
        "",
        "Counts by state:",
    ]

    assert result["total_rows_processed"] == 8
    assert result["valid_rows"] == 4
    assert result["rejected_rows"] == 4
    assert result["reconciliation_difference"] == 0


def test_windows_file_release(tmp_path):
    """Release the input file handle after ETL completes."""
    input_path = tmp_path / "input.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(
        "activity_year,action_taken,loan_amount,income,lei\n"
        "2020,1,100000,50000,12345678901234\n",
        encoding="utf-8",
    )

    etl_hmda(input_path, output_dir, chunksize=1)
    input_path.unlink()

    assert not input_path.exists()


def test_chunk_reconciliation(tmp_path):
    """Do not lose or duplicate records across chunk boundaries."""
    rows = ["2020,1,100000,50000,12345678901234" for _ in range(1000)]
    input_path = tmp_path / "input.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(
        "activity_year,action_taken,loan_amount,income,lei\n"
        + "\n".join(rows),
        encoding="utf-8",
    )

    result = etl_hmda(input_path, output_dir, chunksize=100)

    assert result["total_rows_processed"] == 1000
    assert result["valid_rows"] == 1000
    assert result["rejected_rows"] == 0
    assert result["reconciliation_difference"] == 0

    clean_path = output_dir / "hmda_clean.parquet"
    assert clean_path.exists()
    assert len(pd.read_parquet(clean_path)) == 1000


def test_applicant_race_1_dtype_mismatch_regression(tmp_path):
    """Test that applicant_race-1 column does not cause schema mismatch between chunks."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei,applicant_race-1
2020,1,100000,50000,12345678901234,1
2020,1,100000,50000,12345678901234,2
2020,1,100000,50000,12345678901234,1
2020,1,100000,50000,12345678901234,
"""
    input_path = tmp_path / "input.csv"
    output_dir = tmp_path / "output"
    input_path.write_text(csv_text, encoding="utf-8")

    result = etl_hmda(input_path, output_dir, chunksize=2)

    # Check reconciliation
    assert result["reconciliation_difference"] == 0
    assert result["valid_rows"] == 4
    assert result["rejected_rows"] == 0

    # Check the output file
    clean_path = output_dir / "hmda_clean.parquet"
    assert clean_path.exists()
    df = pd.read_parquet(clean_path)
    assert len(df) == 4
    # Check the values of applicant_race-1
    assert df.iloc[0]["applicant_race-1"] == "1"
    assert df.iloc[1]["applicant_race-1"] == "2"
    assert df.iloc[2]["applicant_race-1"] == "1"
    assert pd.isna(df.iloc[3]["applicant_race-1"])


def test_multi_file_discovery_supported_scope(tmp_path):
    """Discover only supported HMDA state-year extracts."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for file_name in [
        "hmda_2023_CA.csv",
        "hmda_2024_TX.csv",
        "hmda_2025_FL.csv",
        "notes.csv",
    ]:
        (raw_dir / file_name).write_text("activity_year,state_code\n", encoding="utf-8")

    discovered = discover_hmda_files(raw_dir)

    assert [source.path.name for source in discovered] == [
        "hmda_2023_CA.csv",
        "hmda_2024_TX.csv",
        "hmda_2025_FL.csv",
    ]
    assert [(source.year, source.state) for source in discovered] == [
        (2023, "CA"),
        (2024, "TX"),
        (2025, "FL"),
    ]


def test_discovery_fails_for_unsupported_state_year_file(tmp_path):
    """Do not silently ignore convention-matching files outside supported scope."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "hmda_2022_CA.csv").write_text(
        "activity_year,state_code\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported HMDA raw file"):
        discover_hmda_files(raw_dir)


def test_multi_file_consolidation_and_reconciliation(tmp_path):
    """Append supported files into one clean and one rejected Parquet dataset."""
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    raw_dir.mkdir()

    (raw_dir / "hmda_2023_CA.csv").write_text(
        "activity_year,state_code,action_taken,loan_amount,income,lei\n"
        "2023,CA,1,100000,50,LEI-CA-1\n"
        "2023,CA,3,0,60,LEI-CA-2\n",
        encoding="utf-8",
    )
    (raw_dir / "hmda_2024_TX.csv").write_text(
        "activity_year,state_code,action_taken,loan_amount,income,lei\n"
        "2024,TX,1,200000,70,LEI-TX-1\n"
        "2024,TX,9,300000,80,LEI-TX-2\n",
        encoding="utf-8",
    )

    result = etl_hmda(raw_dir, output_dir, chunksize=1)

    assert result["total_rows_processed"] == 4
    assert result["valid_rows"] == 2
    assert result["rejected_rows"] == 2
    assert result["reconciliation_difference"] == 0
    assert result["counts_by_source_file"] == {
        "hmda_2023_CA.csv": {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
        "hmda_2024_TX.csv": {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
    }
    assert result["counts_by_year"] == {
        2023: {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
        2024: {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
    }
    assert result["counts_by_state"] == {
        "CA": {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
        "TX": {"total_rows": 2, "valid_rows": 1, "rejected_rows": 1},
    }

    clean_df = pd.read_parquet(output_dir / "hmda_clean.parquet")
    rejected_df = pd.read_parquet(output_dir / "hmda_rejected.parquet")

    assert len(clean_df) == 2
    assert len(rejected_df) == 2
    assert set(clean_df["activity_year"]) == {2023, 2024}
    assert set(clean_df["state_code"]) == {"CA", "TX"}
    assert "rejection_reason" not in clean_df.columns
    assert "rejection_reason" in rejected_df.columns


def test_filename_activity_year_mismatch_fails_clearly(tmp_path):
    """Fail instead of rewriting mismatched activity_year values."""
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "hmda_2025_NY.csv").write_text(
        "activity_year,state_code,action_taken,loan_amount,income,lei\n"
        "2024,NY,1,100000,50,LEI-NY-1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="activity_year values"):
        etl_hmda(raw_dir, output_dir, chunksize=1)


def test_filename_state_mismatch_fails_clearly(tmp_path):
    """Fail instead of rewriting mismatched state_code values."""
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    raw_dir.mkdir()
    (raw_dir / "hmda_2025_IL.csv").write_text(
        "activity_year,state_code,action_taken,loan_amount,income,lei\n"
        "2025,CA,1,100000,50,LEI-IL-1\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="state_code values"):
        etl_hmda(raw_dir, output_dir, chunksize=1)


def test_2023_2024_2025_are_valid_supported_years(tmp_path):
    """Support the initial multi-year ingestion scope."""
    raw_dir = tmp_path / "raw"
    output_dir = tmp_path / "processed"
    raw_dir.mkdir()
    for year, state in [(2023, "CA"), (2024, "TX"), (2025, "FL")]:
        (raw_dir / f"hmda_{year}_{state}.csv").write_text(
            "activity_year,state_code,action_taken,loan_amount,income,lei\n"
            f"{year},{state},1,100000,50,LEI-{state}-{year}\n",
            encoding="utf-8",
        )

    result = etl_hmda(raw_dir, output_dir, chunksize=2)

    assert result["valid_rows"] == 3
    assert result["rejected_rows"] == 0
    assert set(result["counts_by_year"]) == {2023, 2024, 2025}
