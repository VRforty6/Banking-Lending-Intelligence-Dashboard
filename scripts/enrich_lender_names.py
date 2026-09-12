#!/usr/bin/env python3
"""
Enrich analytics.dim_lender with official HMDA institution names.

The script intentionally lives outside the 12M-row LAR ETL path. By default it
fetches official HMDA/FFIEC/CFPB Data Browser filer metadata, writes a local
reference cache, prints validation counts, and does not update production data.

Production updates require explicit flags:
  --apply-schema  runs the idempotent ALTER TABLE migration
  --apply-db      updates only analytics.dim_lender.lender_name
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import load_data


LOGGER = logging.getLogger("enrich_lender_names")

DEFAULT_CACHE_PATH = PROJECT_ROOT / "data" / "reference" / "lender_names.csv"
SCHEMA_SQL = PROJECT_ROOT / "sql" / "08_add_lender_name_to_dim_lender.sql"

DEFAULT_YEARS = (2025, 2024, 2023)
DEFAULT_STATES = ("CA", "TX", "FL", "NY", "IL")
DATA_BROWSER_FILERS_URL = "https://ffiec.cfpb.gov/v2/data-browser-api/view/filers"
SOURCE_LABEL = "Official HMDA Data Browser filers API"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class LenderMetadata:
    lei: str
    lender_name: str | None
    source_year: int | None
    source: str
    status: str


@dataclass(frozen=True)
class ValidationSummary:
    total_warehouse_leis: int
    matched_names: int
    unmatched_leis: int
    duplicate_lei_rows: int
    blank_names: int

    @property
    def match_percentage(self) -> float:
        if self.total_warehouse_leis == 0:
            return 0.0
        return self.matched_names / self.total_warehouse_leis * 100


def normalize_lei(value: object) -> str:
    return str(value or "").strip().upper()


def normalize_name(value: object) -> str | None:
    normalized = " ".join(str(value or "").split())
    return normalized or None


def parse_institutions_response(payload: dict, year: int) -> list[dict[str, object]]:
    institutions = payload.get("institutions")
    if not isinstance(institutions, list):
        raise ValueError("HMDA filer response did not include an institutions list")

    records: list[dict[str, object]] = []
    for item in institutions:
        if not isinstance(item, dict):
            continue

        lei = normalize_lei(item.get("lei") or item.get("LEI") or item.get("institutionId"))
        name = normalize_name(item.get("name") or item.get("institutionName"))
        period = item.get("period") or item.get("year") or year

        records.append(
            {
                "lei": lei,
                "lender_name": name,
                "source_year": int(period),
                "source": SOURCE_LABEL,
            }
        )

    return records


def build_filers_url(year: int, states: Iterable[str]) -> str:
    params = {
        "years": str(year),
        "states": ",".join(states),
    }
    return f"{DATA_BROWSER_FILERS_URL}?{urlencode(params)}"


def fetch_json_with_retry(
    url: str,
    *,
    timeout: float,
    max_retries: int,
    backoff_seconds: float,
    opener: Callable[..., object] = urlopen,
) -> dict:
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            with opener(url, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except HTTPError as exc:
            if exc.code == 404:
                raise
            last_error = exc
            if exc.code not in RETRYABLE_STATUSES or attempt == max_retries:
                raise
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == max_retries:
                raise

        sleep_for = backoff_seconds * (2**attempt)
        LOGGER.warning("Retrying HMDA metadata request after error: %s", last_error)
        time.sleep(sleep_for)

    raise RuntimeError(f"HMDA metadata request failed: {last_error}")


def fetch_filer_metadata(
    warehouse_leis: Iterable[str],
    years: Iterable[int],
    states: Iterable[str],
    *,
    timeout: float,
    max_retries: int,
    backoff_seconds: float,
    throttle_seconds: float,
    opener: Callable[..., object] = urlopen,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    warehouse_lei_set = {normalize_lei(lei) for lei in warehouse_leis if normalize_lei(lei)}
    for year in years:
        url = build_filers_url(year, states)
        LOGGER.info("Fetching HMDA filer metadata for %s", year)
        payload = fetch_json_with_retry(
            url,
            timeout=timeout,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
            opener=opener,
        )
        year_records = parse_institutions_response(payload, year)
        matched_year_records = [
            record for record in year_records if normalize_lei(record.get("lei")) in warehouse_lei_set
        ]
        LOGGER.info(
            "Fetched %s institution rows for %s; %s matched warehouse LEIs",
            len(year_records),
            year,
            len(matched_year_records),
        )
        records.extend(matched_year_records)
        if throttle_seconds > 0:
            time.sleep(throttle_seconds)
    return records


def count_duplicate_lei_rows(records: Iterable[dict[str, object]]) -> int:
    seen: set[tuple[int, str, str | None]] = set()
    duplicates = 0
    for record in records:
        key = (
            int(record["source_year"]),
            normalize_lei(record["lei"]),
            normalize_name(record.get("lender_name")),
        )
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return duplicates


def choose_lender_names(
    warehouse_leis: Iterable[str],
    source_records: Iterable[dict[str, object]],
    years: Iterable[int],
) -> list[LenderMetadata]:
    by_year_lei: dict[tuple[int, str], set[str | None]] = {}
    for record in source_records:
        lei = normalize_lei(record.get("lei"))
        if not lei:
            continue
        year = int(record["source_year"])
        by_year_lei.setdefault((year, lei), set()).add(normalize_name(record.get("lender_name")))

    selected: list[LenderMetadata] = []
    for lei in sorted({normalize_lei(value) for value in warehouse_leis if normalize_lei(value)}):
        match: LenderMetadata | None = None
        for year in years:
            names = by_year_lei.get((int(year), lei), set())
            usable_names = sorted(name for name in names if name)
            if len(usable_names) == 1:
                match = LenderMetadata(lei, usable_names[0], int(year), SOURCE_LABEL, "matched")
                break
            if len(usable_names) > 1:
                match = LenderMetadata(lei, None, int(year), SOURCE_LABEL, "duplicate_name_conflict")
                break
            if names and not usable_names:
                match = LenderMetadata(lei, None, int(year), SOURCE_LABEL, "blank_name")
                break

        if match is None:
            match = LenderMetadata(lei, None, None, SOURCE_LABEL, "unmatched")
        selected.append(match)
    return selected


def summarize_results(
    warehouse_leis: Iterable[str],
    selected: Iterable[LenderMetadata],
    source_records: Iterable[dict[str, object]],
) -> ValidationSummary:
    selected_list = list(selected)
    records_list = list(source_records)
    return ValidationSummary(
        total_warehouse_leis=len({normalize_lei(value) for value in warehouse_leis if normalize_lei(value)}),
        matched_names=sum(1 for item in selected_list if item.status == "matched" and item.lender_name),
        unmatched_leis=sum(1 for item in selected_list if item.status != "matched"),
        duplicate_lei_rows=count_duplicate_lei_rows(records_list),
        blank_names=sum(1 for item in selected_list if item.status == "blank_name"),
    )


def write_cache(path: Path, selected: Iterable[LenderMetadata]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=["lei", "lender_name", "source_year", "source", "status"],
        )
        writer.writeheader()
        for item in selected:
            writer.writerow(
                {
                    "lei": item.lei,
                    "lender_name": item.lender_name or "",
                    "source_year": item.source_year or "",
                    "source": item.source,
                    "status": item.status,
                }
            )


def read_cache(path: Path) -> list[LenderMetadata]:
    with path.open("r", newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        rows: list[LenderMetadata] = []
        for row in reader:
            source_year = int(row["source_year"]) if row.get("source_year") else None
            rows.append(
                LenderMetadata(
                    lei=normalize_lei(row.get("lei")),
                    lender_name=normalize_name(row.get("lender_name")),
                    source_year=source_year,
                    source=row.get("source") or SOURCE_LABEL,
                    status=row.get("status") or "unknown",
                )
            )
    return rows


def get_engine() -> Engine:
    env = load_data.load_environment()
    return create_engine(load_data.get_db_connection_string(env))


def get_warehouse_leis(engine: Engine) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT lei FROM analytics.dim_lender WHERE lei IS NOT NULL ORDER BY lei")
        ).fetchall()
    return [row[0] for row in rows]


def apply_schema(engine: Engine) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(sql))


def update_lender_names(engine: Engine, selected: Iterable[LenderMetadata]) -> int:
    matched = [item for item in selected if item.status == "matched" and item.lender_name]
    update_sql = text(
        """
        UPDATE analytics.dim_lender
        SET lender_name = :lender_name
        WHERE lei = :lei
        """
    )
    with engine.begin() as conn:
        for item in matched:
            conn.execute(update_sql, {"lei": item.lei, "lender_name": item.lender_name})
    return len(matched)


def print_summary(summary: ValidationSummary) -> None:
    print(f"Total warehouse LEIs: {summary.total_warehouse_leis}")
    print(f"Matched names: {summary.matched_names}")
    print(f"Unmatched LEIs: {summary.unmatched_leis}")
    print(f"Duplicate LEIs in enrichment source: {summary.duplicate_lei_rows}")
    print(f"Blank names: {summary.blank_names}")
    print(f"Match percentage: {summary.match_percentage:.2f}%")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_CACHE_PATH)
    parser.add_argument("--years", default="2025,2024,2023")
    parser.add_argument("--states", default="CA,TX,FL,NY,IL")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=1.0)
    parser.add_argument("--throttle-seconds", type=float, default=0.5)
    parser.add_argument("--use-cache", action="store_true", help="Read existing cache instead of fetching API metadata")
    parser.add_argument("--apply-schema", action="store_true", help="Apply idempotent lender_name schema migration")
    parser.add_argument("--apply-db", action="store_true", help="Update analytics.dim_lender.lender_name")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    args = parse_args()
    years = tuple(int(value.strip()) for value in args.years.split(",") if value.strip())
    states = tuple(value.strip().upper() for value in args.states.split(",") if value.strip())

    engine = get_engine()
    warehouse_leis = get_warehouse_leis(engine)

    if args.apply_schema:
        LOGGER.info("Applying idempotent schema migration: %s", SCHEMA_SQL)
        apply_schema(engine)

    if args.use_cache:
        selected = read_cache(args.cache_path)
        source_records: list[dict[str, object]] = []
    else:
        source_records = fetch_filer_metadata(
            warehouse_leis,
            years,
            states,
            timeout=args.timeout,
            max_retries=args.max_retries,
            backoff_seconds=args.backoff_seconds,
            throttle_seconds=args.throttle_seconds,
        )
        selected = choose_lender_names(warehouse_leis, source_records, years)
        write_cache(args.cache_path, selected)
        LOGGER.info("Wrote lender-name cache: %s", args.cache_path)

    summary = summarize_results(warehouse_leis, selected, source_records)
    print_summary(summary)

    if args.apply_db:
        updated = update_lender_names(engine, selected)
        print(f"Updated analytics.dim_lender.lender_name rows: {updated}")
    else:
        print("Dry run only: database lender_name values were not updated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
