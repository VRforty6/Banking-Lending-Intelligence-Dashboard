import pandas as pd
import pytest
from etl_hmda import clean_chunk, validate_chunk, etl_hmda


def test_numeric_conversion(tmp_path):
    """Test numeric conversion of activity_year, action_taken, loan_amount, income."""
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

    # Read the whole CSV to check dtypes (not using chunks for simplicity in test)
    df = pd.read_csv(csv_path, keep_default_na=True, na_values=["", "NA", "N/A", "Exempt"])
    cleaned = clean_chunk(df)

    # Check dtypes
    assert cleaned["activity_year"].dtype == "Int64"
    assert cleaned["action_taken"].dtype == "Int64"
    assert pd.api.types.is_float_dtype(cleaned["loan_amount"])
    assert pd.api.types.is_float_dtype(cleaned["income"])
    assert cleaned["lei"].dtype == "string"

    # Check specific values
    # Row 0: all valid
    assert cleaned.loc[0, "activity_year"] == 2020
    assert cleaned.loc[0, "action_taken"] == 1
    assert cleaned.loc[0, "loan_amount"] == 100000.0
    assert cleaned.loc[0, "income"] == 50000.0
    assert cleaned.loc[0, "lei"] == "12345678901234"

    # Row 1: all valid
    assert cleaned.loc[1, "activity_year"] == 2021
    assert cleaned.loc[1, "action_taken"] == 2
    assert cleaned.loc[1, "loan_amount"] == 200000.0
    assert cleaned.loc[1, "income"] == 60000.0
    assert cleaned.loc[1, "lei"] == "23456789012345"

    # Row 2: missing activity_year -> becomes NaN -> <NA> in Int64
    assert pd.isna(cleaned.loc[2, "activity_year"])
    assert cleaned.loc[2, "action_taken"] == 3
    assert cleaned.loc[2, "loan_amount"] == 300000.0
    assert cleaned.loc[2, "income"] == 70000.0
    assert cleaned.loc[2, "lei"] == "34567890123456"

    # Row 3: missing loan_amount -> becomes NaN -> <NA> in Float64
    assert cleaned.loc[3, "activity_year"] == 2022
    assert cleaned.loc[3, "action_taken"] == 4
    assert pd.isna(cleaned.loc[3, "loan_amount"])
    assert cleaned.loc[3, "income"] == 80000.0
    assert cleaned.loc[3, "lei"] == "45678901234567"

    # Row 4: missing income -> becomes NaN -> <NA> in Float64
    assert cleaned.loc[4, "activity_year"] == 2023
    assert cleaned.loc[4, "action_taken"] == 5
    assert cleaned.loc[4, "loan_amount"] == 500000.0
    assert pd.isna(cleaned.loc[4, "income"])
    assert cleaned.loc[4, "lei"] == "56789012345678"

    # Row 5: loan_amount = 0 -> becomes 0.0 (valid for conversion, but will be rejected later)
    assert cleaned.loc[5, "activity_year"] == 2024
    assert cleaned.loc[5, "action_taken"] == 6
    assert cleaned.loc[5, "loan_amount"] == 0.0
    assert cleaned.loc[5, "income"] == 90000.0
    assert cleaned.loc[5, "lei"] == "67890123456789"

    # Row 6: loan_amount = -100 -> becomes -100.0
    assert cleaned.loc[6, "activity_year"] == 2025
    assert cleaned.loc[6, "action_taken"] == 7
    assert cleaned.loc[6, "loan_amount"] == -100.0
    assert cleaned.loc[6, "income"] == 100000.0
    assert cleaned.loc[6, "lei"] == "78901234567890"

    # Row 7: lei empty string -> becomes pd.NA -> <NA> in string
    assert cleaned.loc[7, "activity_year"] == 2026
    assert cleaned.loc[7, "action_taken"] == 8
    assert cleaned.loc[7, "loan_amount"] == 100000.0
    assert cleaned.loc[7, "income"] == 110000.0
    assert pd.isna(cleaned.loc[7, "lei"])

    # Row 8: lei = "9" -> becomes "9" (but note: action_taken=9 is invalid)
    assert cleaned.loc[8, "activity_year"] == 2027
    assert cleaned.loc[8, "action_taken"] == 9
    assert cleaned.loc[8, "loan_amount"] == 100000.0
    assert cleaned.loc[8, "income"] == 120000.0
    assert cleaned.loc[8, "lei"] == "9"

    # Row 9: lei = "NA" string -> becomes pd.NA
    assert pd.isna(cleaned.loc[9, "lei"])

    # Row 10: lei = "nan" string -> becomes pd.NA
    assert pd.isna(cleaned.loc[10, "lei"])

    # Row 11: lei = "<NA>" string -> becomes pd.NA
    assert pd.isna(cleaned.loc[11, "lei"])


def test_action_taken_validation(tmp_path):
    """Test action_taken validation: valid values 1-8, others rejected."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
2020,2,100000,50000,12345678901234
2020,0,100000,50000,12345678901234
2020,9,100000,50000,12345678901234
2020,,100000,50000,12345678901234
2020,abc,100000,50000,12345678901234
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    df = pd.read_csv(csv_path, keep_default_na=True, na_values=["", "NA", "N/A", "Exempt"])
    cleaned = clean_chunk(df)
    valid, rejected, counts = validate_chunk(cleaned)

    # Check counts
    assert len(valid) == 2  # action_taken 1 and 2
    assert len(rejected) == 4  # 0, 9, empty, abc
    assert counts["invalid_action_taken"] == 4

    # Check rejected reasons
    assert all(r == "invalid_action_taken" for r in rejected["rejection_reason"])

    # Check that valid rows have correct action_taken
    assert set(valid["action_taken"].dropna().astype(int)) == {1, 2}


def test_row_retention_and_rejection(tmp_path):
    """Test exactly six rows: one valid, four each missing one condition, one valid."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,
2020,1,0,50000,12345678901234
2020,0,100000,50000,12345678901234
2020,1,100000,50000,12345678901234
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    df = pd.read_csv(csv_path, keep_default_na=True, na_values=["", "NA", "N/A", "Exempt"])
    cleaned = clean_chunk(df)
    valid, rejected, counts = validate_chunk(cleaned)

    # Check totals
    assert len(df) == 6
    assert len(valid) == 2  # first and last
    assert len(rejected) == 4  # middle four
    assert len(valid) + len(rejected) == len(df)

    # Check each reason occurs once
    assert counts["missing_activity_year"] == 1  # second row
    assert counts["missing_lei"] == 1  # third row
    assert counts["invalid_loan_amount"] == 1  # fourth row (loan_amount=0)
    assert counts["invalid_action_taken"] == 1  # fifth row (action_taken=0)

    # Check rejected reasons
    expected_reasons = [
        "missing_activity_year",
        "missing_lei",
        "invalid_loan_amount",
        "invalid_action_taken"
    ]
    assert sorted(rejected["rejection_reason"].tolist()) == sorted(expected_reasons)


def test_multiple_rejection_reasons(tmp_path):
    """Test one row that fails multiple rules."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
,0,0,,
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    df = pd.read_csv(csv_path, keep_default_na=True, na_values=["", "NA", "N/A", "Exempt"])
    cleaned = clean_chunk(df)
    valid, rejected, counts = validate_chunk(cleaned)

    # Check that the row is rejected
    assert len(valid) == 0
    assert len(rejected) == 1

    # Check that all four reasons are counted
    assert counts["missing_activity_year"] == 1
    assert counts["missing_lei"] == 1
    assert counts["invalid_action_taken"] == 1
    assert counts["invalid_loan_amount"] == 1

    # Check that the rejection_reason contains all four labels in deterministic order
    # Order of checks: missing_activity_year, missing_lei, invalid_action_taken, invalid_loan_amount
    assert rejected["rejection_reason"].iloc[0] == "missing_activity_year;missing_lei;invalid_action_taken;invalid_loan_amount"


def test_validation_report(tmp_path):
    """Test validation report matches expected format and counts."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,
2020,1,0,50000,12345678901234
2020,0,100000,50000,12345678901234
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    output_dir = tmp_path / "output"
    result = etl_hmda(csv_path, output_dir, chunksize=2)  # small chunksize to test chunking

    # Check return value
    assert result["total_rows_processed"] == 5
    assert result["valid_rows"] == 1
    assert result["rejected_rows"] == 4
    assert result["reconciliation_difference"] == 0
    assert result["failed_activity_year"] == 1
    assert result["failed_lei"] == 1
    assert result["failed_loan_amount"] == 1
    assert result["failed_action_taken"] == 1

    # Check that output files exist
    assert (output_dir / "hmda_clean.parquet").exists()
    assert (output_dir / "hmda_rejected.parquet").exists()
    assert (output_dir / "validation_report.txt").exists()

    # Check the report content
    report_text = (output_dir / "validation_report.txt").read_text(encoding="utf-8")
    expected_lines = [
        "HMDA ETL Validation Report",
        "Total rows processed: 5",
        "Valid rows: 1",
        "Rejected rows: 4",
        "Reconciliation difference: 0",
        "Failed activity_year (missing): 1",
        "Failed lei (missing): 1",
        "Failed loan_amount (invalid): 1",
        "Failed action_taken (invalid): 1"
    ]
    for line in expected_lines:
        assert line in report_text


def test_windows_file_release(tmp_path):
    """Test that the input file can be deleted immediately after ETL runs."""
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    output_dir = tmp_path / "output"
    # Run ETL
    etl_hmda(csv_path, output_dir, chunksize=100_000)

    # On Windows, we cannot delete an open file.
    # Try to delete the file; if it fails, the test will fail.
    # This test passes if the file handle is closed.
    csv_path.unlink()  # Should not raise an error if the file is closed


def test_chunk_reconciliation(tmp_path):
    """Test that with chunksize=2, no rows are lost or duplicated."""
    # Create 10 rows of alternating valid and invalid to test chunk boundaries
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234   # valid
,1,100000,50000,12345678901234       # invalid: missing activity_year
2020,1,100000,50000,12345678901234   # valid
,1,100000,50000,12345678901234       # invalid: missing activity_year
2020,1,100000,50000,12345678901234   # valid
,1,100000,50000,12345678901234       # invalid: missing activity_year
2020,1,100000,50000,12345678901234   # valid
,1,100000,50000,12345678901234       # invalid: missing activity_year
2020,1,100000,50000,12345678901234   # valid
,1,100000,50000,12345678901234       # invalid: missing activity_year
"""
    # Remove comments
    csv_text = """activity_year,action_taken,loan_amount,income,lei
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
2020,1,100000,50000,12345678901234
,1,100000,50000,12345678901234
"""
    csv_path = tmp_path / "input.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    output_dir = tmp_path / "output"
    result = etl_hmda(csv_path, output_dir, chunksize=2)  # chunksize=2

    # Expect 5 valid, 5 rejected
    assert result["total_rows_processed"] == 10
    assert result["valid_rows"] == 5
    assert result["rejected_rows"] == 5
    assert result["reconciliation_difference"] == 0
    assert result["failed_activity_year"] == 5  # each invalid row has missing activity_year
    assert result["failed_lei"] == 0
    assert result["failed_loan_amount"] == 0
    assert result["failed_action_taken"] == 0

    # Also verify that the parquet files have the correct number of rows
    # Read the parquet files and count rows
    if result["valid_rows"] > 0:
        df_valid = pd.read_parquet(output_dir / "hmda_clean.parquet")
        assert len(df_valid) == result["valid_rows"]
    if result["rejected_rows"] > 0:
        df_rejected = pd.read_parquet(output_dir / "hmda_rejected.parquet")
        assert len(df_rejected) == result["rejected_rows"]