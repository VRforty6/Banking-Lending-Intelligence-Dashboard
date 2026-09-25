"""Generate the five-state Census county reference seed SQL.

Input is the extracted 2025 National Counties Gazetteer pipe-delimited text file.
The generated SQL preserves five-character GEOID strings and loads only the
states present in the HMDA warehouse.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


SUPPORTED_COUNTS = {
    "CA": 58,
    "FL": 67,
    "IL": 102,
    "NY": 62,
    "TX": 254,
}
SOURCE_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2025_Gazetteer/2025_Gaz_counties_national.zip"
)


def sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def build_seed(source_path: Path) -> str:
    rows: list[dict[str, str]] = []
    with source_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter="|")
        required = {"USPS", "GEOID", "NAME", "INTPTLAT", "INTPTLONG"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Gazetteer input does not contain the expected county columns")
        rows = [row for row in reader if row["USPS"] in SUPPORTED_COUNTS]

    actual_counts = {
        state: sum(row["USPS"] == state for row in rows) for state in SUPPORTED_COUNTS
    }
    if actual_counts != SUPPORTED_COUNTS:
        raise ValueError(
            f"Unexpected county counts: expected {SUPPORTED_COUNTS}, got {actual_counts}"
        )

    geoids = [row["GEOID"] for row in rows]
    if len(geoids) != len(set(geoids)) or any(len(geoid) != 5 for geoid in geoids):
        raise ValueError("County GEOIDs must be unique five-character strings")

    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    values = []
    for row in sorted(rows, key=lambda item: item["GEOID"]):
        values.append(
            "    ("
            + ", ".join(
                [
                    sql_text(row["GEOID"]),
                    sql_text(row["USPS"]),
                    sql_text(row["NAME"]),
                    row["INTPTLAT"],
                    row["INTPTLONG"],
                    "2025",
                ]
            )
            + ")"
        )

    return f"""-- GENERATED FILE. Do not hand-edit.
-- Source: {SOURCE_URL}
-- Extracted file SHA-256: {source_sha256}
-- Transformation: filter USPS to CA, FL, IL, NY, TX; retain GEOID, NAME,
-- representative latitude/longitude; preserve GEOID as text.

TRUNCATE TABLE analytics.ref_county;

INSERT INTO analytics.ref_county (
    county_fips,
    state_code,
    county_name,
    internal_latitude,
    internal_longitude,
    source_vintage
)
VALUES
{',\n'.join(values)};
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    generated = build_seed(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generated, encoding="utf-8", newline="\n")
    print(f"Wrote {sum(SUPPORTED_COUNTS.values())} counties to {args.output}")


if __name__ == "__main__":
    main()
