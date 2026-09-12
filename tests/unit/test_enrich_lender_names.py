import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from scripts.enrich_lender_names import (
    choose_lender_names,
    fetch_filer_metadata,
    fetch_json_with_retry,
    normalize_name,
    parse_institutions_response,
    summarize_results,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_parse_valid_api_response_extracts_names():
    payload = {
        "institutions": [
            {"lei": "abc123", "name": "Example Bank", "period": 2025},
        ]
    }

    records = parse_institutions_response(payload, 2025)

    assert records == [
        {
            "lei": "ABC123",
            "lender_name": "Example Bank",
            "source_year": 2025,
            "source": "Official HMDA Data Browser filers API",
        }
    ]


def test_parse_missing_name_keeps_blank_for_validation():
    payload = {"institutions": [{"lei": "ABC123", "period": 2025}]}

    records = parse_institutions_response(payload, 2025)

    assert records[0]["lender_name"] is None


def test_normalize_name_collapses_whitespace_without_rewording():
    assert normalize_name("  First   National\tBank  ") == "First National Bank"


def test_http_404_is_not_retried():
    calls = {"count": 0}

    def opener(url, timeout):
        calls["count"] += 1
        raise HTTPError(url, 404, "not found", hdrs=None, fp=BytesIO())

    with pytest.raises(HTTPError):
        fetch_json_with_retry(
            "https://example.test/missing",
            timeout=1,
            max_retries=3,
            backoff_seconds=0,
            opener=opener,
        )

    assert calls["count"] == 1


def test_retryable_http_error_is_retried_then_succeeds():
    calls = {"count": 0}

    def opener(url, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HTTPError(url, 503, "try later", hdrs=None, fp=BytesIO())
        return FakeResponse({"institutions": []})

    payload = fetch_json_with_retry(
        "https://example.test/retry",
        timeout=1,
        max_retries=3,
        backoff_seconds=0,
        opener=opener,
    )

    assert payload == {"institutions": []}
    assert calls["count"] == 2


def test_fetch_filer_metadata_filters_to_warehouse_leis():
    requested_urls = []

    def opener(url, timeout):
        requested_urls.append(url)
        return FakeResponse(
            {
                "institutions": [
                    {"lei": "AAA", "name": "Warehouse Bank", "period": 2025},
                    {"lei": "ZZZ", "name": "Outside Bank", "period": 2025},
                ]
            }
        )

    records = fetch_filer_metadata(
        ["AAA"],
        [2025],
        ["CA", "TX"],
        timeout=1,
        max_retries=0,
        backoff_seconds=0,
        throttle_seconds=0,
        opener=opener,
    )

    assert len(records) == 1
    assert records[0]["lei"] == "AAA"
    assert records[0]["lender_name"] == "Warehouse Bank"
    assert "years=2025" in requested_urls[0]
    assert "states=CA%2CTX" in requested_urls[0]


def test_latest_year_selection_prefers_2025_then_2024_then_2023():
    records = [
        {"lei": "AAA", "lender_name": "Older Name", "source_year": 2024},
        {"lei": "AAA", "lender_name": "Latest Name", "source_year": 2025},
        {"lei": "BBB", "lender_name": "Only 2023 Name", "source_year": 2023},
    ]

    selected = choose_lender_names(["AAA", "BBB"], records, [2025, 2024, 2023])
    by_lei = {item.lei: item for item in selected}

    assert by_lei["AAA"].lender_name == "Latest Name"
    assert by_lei["AAA"].source_year == 2025
    assert by_lei["BBB"].lender_name == "Only 2023 Name"
    assert by_lei["BBB"].source_year == 2023


def test_duplicate_same_year_same_name_is_deduped():
    records = [
        {"lei": "AAA", "lender_name": "Example Bank", "source_year": 2025},
        {"lei": "AAA", "lender_name": "Example Bank", "source_year": 2025},
    ]

    selected = choose_lender_names(["AAA"], records, [2025])

    assert selected[0].status == "matched"
    assert selected[0].lender_name == "Example Bank"


def test_duplicate_same_year_conflicting_names_is_not_invented():
    records = [
        {"lei": "AAA", "lender_name": "Example Bank", "source_year": 2025},
        {"lei": "AAA", "lender_name": "Different Bank", "source_year": 2025},
    ]

    selected = choose_lender_names(["AAA"], records, [2025])

    assert selected[0].status == "duplicate_name_conflict"
    assert selected[0].lender_name is None


def test_unmatched_lei_preserves_null_lender_name():
    selected = choose_lender_names(["AAA"], [], [2025, 2024, 2023])

    assert selected[0].status == "unmatched"
    assert selected[0].lender_name is None


def test_summary_counts_unmatched_blank_and_duplicates():
    warehouse = ["AAA", "BBB", "CCC"]
    records = [
        {"lei": "AAA", "lender_name": "Example Bank", "source_year": 2025},
        {"lei": "AAA", "lender_name": "Example Bank", "source_year": 2025},
        {"lei": "BBB", "lender_name": None, "source_year": 2025},
    ]
    selected = choose_lender_names(warehouse, records, [2025])

    summary = summarize_results(warehouse, selected, records)

    assert summary.total_warehouse_leis == 3
    assert summary.matched_names == 1
    assert summary.unmatched_leis == 2
    assert summary.duplicate_lei_rows == 1
    assert summary.blank_names == 1
