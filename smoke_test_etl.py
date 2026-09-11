import tempfile
import os
import pandas as pd
from etl_hmda import etl_hmda

def test_etl_on_small_data():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, 'input.csv')
        output_dir = os.path.join(tmpdir, 'output')

        # Create a small CSV with two chunks (chunksize=2 will give two chunks of 2 rows each)
        csv_data = """activity_year,action_taken,loan_amount,income,lei,applicant_race-1
2020,1,100000,50000,12345678901234,1
2020,1,100000,50000,12345678901234,2
2020,1,100000,50000,12345678901234,1
2020,1,100000,50000,12345678901234,
"""
        with open(input_path, 'w') as f:
            f.write(csv_data)

        # Run the ETL
        result = etl_hmda(input_path, output_dir, chunksize=2)

        print("Result:", result)

        # Check that we processed 4 rows
        assert result['total_rows_processed'] == 4
        assert result['valid_rows'] == 4
        assert result['rejected_rows'] == 0
        assert result['reconciliation_difference'] == 0

        # Check the output file
        clean_path = os.path.join(output_dir, 'hmda_clean.parquet')
        assert os.path.exists(clean_path)
        df = pd.read_parquet(clean_path)
        assert len(df) == 4
        # Check the applicant_race-1 column
        assert df.iloc[0]['applicant_race-1'] == '1'
        assert df.iloc[1]['applicant_race-1'] == '2'
        assert df.iloc[2]['applicant_race-1'] == '1'
        assert pd.isna(df.iloc[3]['applicant_race-1'])

        print("All tests passed!")

if __name__ == '__main__':
    test_etl_on_small_data()