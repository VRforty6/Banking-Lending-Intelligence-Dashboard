import csv
import sys

def infer_type(values):
    # values is list of strings from sample rows (excluding header)
    # Treat empty string or 'NA' as missing
    non_missing = [v for v in values if v not in ('', 'NA')]
    if not non_missing:
        return 'string'  # unknown
    # Try to see if all can be parsed as float
    is_float = True
    for v in non_missing:
        try:
            float(v)
        except ValueError:
            is_float = False
            break
    if is_float:
        # Check if all are actually integers (no decimal part)
        is_int = True
        for v in non_missing:
            f = float(v)
            if not f.is_integer():
                is_int = False
                break
        if is_int:
            return 'integer'
        else:
            return 'numeric'
    else:
        return 'string'

def main():
    csv_path = r'data/raw/state_CA.csv'
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Sample first 1000 rows for type inference
        sample = []
        for i, row in enumerate(reader):
            if i >= 1000:
                break
            sample.append(row)
    # Transpose sample to columns
    cols = list(zip(*sample)) if sample else [ [] for _ in header ]
    # Build rows for markdown
    lines = []
    lines.append('| Column Name | Data Type | Description |')
    lines.append('|-------------|-----------|-------------|')
    for col_name, col_vals in zip(header, cols):
        dtype = infer_type(col_vals)
        # Provide a brief description based on name (placeholder)
        desc = f'Field: {col_name}'  # generic
        lines.append(f'| {col_name} | {dtype} | {desc} |')
    with open('docs/data_dictionary.md', 'w', encoding='utf-8') as out:
        out.write('\n'.join(lines))

if __name__ == '__main__':
    main()