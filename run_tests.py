#!/usr/bin/env python3
"""
Test runner for the ETL pipeline.
"""
import subprocess
import sys

if __name__ == '__main__':
    # Run pytest on the test_etl.py file
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/unit/test_etl.py', '-v'],
                            capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)