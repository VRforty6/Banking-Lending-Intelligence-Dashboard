#!/usr/bin/env bash
# Generate data dictionary for state_CA.csv
INPUT="data/raw/state_CA.csv"
HEADER=$(head -1 "$INPUT")
OUTPUT="./dict.txt"
echo "| Column Name | Data Type | Description | Nullable? | Notes |" > "$OUTPUT"
echo "|-------------|-----------|-------------|-----------|-------|" >> "$OUTPUT"
IFS=',' read -ra COLS <<< "$HEADER"
for col in "${COLS[@]}"; do
    # Determine data type
    if [[ "$col" =~ (_amount|_value|_ratio|_rate|_percent|_amount|_score|_income|_percent|_percent|_percent|_price|_fee|_cost|_limit|_ratio|_percentage|_pct|_ratio) ]]; then
        dtype="numeric"
    elif [[ "$col" =~ (_year|^year$|_date) ]]; then
        dtype="integer"
    elif [[ "$col" =~ (_flag|_type|_code|_status|_indicator|_flag) ]]; then
        dtype="integer (coded)"
    else
        dtype="string"
    fi
    # Description: make readable
    desc=$(echo "$col" | tr '_' ' ' | sed -e 's/\b\(.\)/\u\1/g')
    # For known acronyms, we could adjust but keep simple
    echo "| $col | $dtype | $desc | Yes | May require lookup from HMDA documentation |" >> "$OUTPUT"
done