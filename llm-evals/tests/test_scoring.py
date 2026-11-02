"""Unit tests for the scoring rules. The harness is test tooling, so it gets tests too."""

from __future__ import annotations

import pytest

from llm_evals.scoring import (
    completeness_score,
    fingerprint,
    match_line_items,
    normalize_text,
    numbers_close,
    score_case,
    values_match,
)

EXPECTED = {
    "vendor": "Northwind Supplies",
    "invoice_number": "NW-10342",
    "invoice_date": "2026-03-14",
    "currency": "USD",
    "subtotal": 423.0,
    "tax": 33.84,
    "total": 456.84,
    "line_items": [
        {"description": "Copier paper A4 80 gsm (box)", "quantity": 10, "unit_price": 24.5, "amount": 245.0},
        {"description": "Toner cartridge black", "quantity": 2, "unit_price": 89.0, "amount": 178.0},
    ],
}


def exact_copy() -> dict:
    import copy

    return copy.deepcopy(EXPECTED)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("Northwind  Supplies", "northwind supplies"),
        ("Aster & Oak Furniture", "aster oak furniture"),
        ("  Kestrel Logistics GmbH.  ", "kestrel logistics gmbh"),
        ("Blue-Birch Printing", "blue birch printing"),
    ],
)
def test_normalize_text(raw: str, normalized: str) -> None:
    assert normalize_text(raw) == normalized


@pytest.mark.parametrize(
    ("expected", "actual", "close"),
    [
        (100.0, 101.9, True),  # within 2%
        (100.0, 102.5, False),  # outside 2%
        (0.10, 0.11, True),  # within 0.01 absolute
        (0.10, 0.12, False),
        (-50.0, -50.5, True),
        (0.0, 0.0, True),
    ],
)
def test_numbers_close(expected: float, actual: float, close: bool) -> None:
    assert numbers_close(expected, actual) is close


def test_values_match_rules() -> None:
    assert values_match("total", 456.84, 456.84) == (True, "")
    assert values_match("total", 456.84, "456.84")[0] is False  # strings are not numbers
    assert values_match("tax", None, None) == (True, "")
    assert values_match("tax", None, 5.0) == (False, "expected null")
    assert values_match("vendor", "Acme Ltd", None) == (False, "missing")
    assert values_match("vendor", "Acme, Ltd.", "acme ltd") == (True, "")


def test_fingerprint_ignores_case_punctuation_and_number_format() -> None:
    a = fingerprint({"description": "Toner cartridge, black", "quantity": 2})
    b = fingerprint({"description": "toner cartridge black", "quantity": 2.0})
    assert a == b


def test_reordered_items_match_by_fingerprint() -> None:
    actual = exact_copy()
    actual["line_items"].reverse()
    pairs, extras = match_line_items(EXPECTED["line_items"], actual["line_items"])
    assert [(e, a, m) for e, a, m in pairs] == [(0, 1, "fingerprint"), (1, 0, "fingerprint")]
    assert extras == []
    score = score_case("reordered", EXPECTED, actual, latency_ms=1.0)
    assert score.passed is True
    assert score.field_accuracy == 1.0


def test_missing_item_counts_as_one_failed_check() -> None:
    actual = exact_copy()
    actual["line_items"].pop()
    score = score_case("missing", EXPECTED, actual, latency_ms=1.0)
    failed = [check for check in score.checks if not check.passed]
    assert [check.name for check in failed] == ["line_items[1].present"]
    assert score.passed is False
    # 7 scalar checks + 4 checks for the matched item + 1 missing = 12 checks, 11 passed
    assert score.field_accuracy == pytest.approx(11 / 12)


def test_extra_item_is_a_failure() -> None:
    actual = exact_copy()
    actual["line_items"].append({"description": "Mystery fee", "quantity": 1, "unit_price": 5.0, "amount": 5.0})
    score = score_case("extra", EXPECTED, actual, latency_ms=1.0)
    names = [check.name for check in score.checks if not check.passed]
    assert names == ["line_items.extra[2]"]


def test_positional_fallback_when_description_differs() -> None:
    actual = exact_copy()
    actual["line_items"][1]["description"] = "Black toner"  # fingerprint changes, position does not
    pairs, _ = match_line_items(EXPECTED["line_items"], actual["line_items"])
    assert pairs[1] == (1, 1, "position")
    score = score_case("positional", EXPECTED, actual, latency_ms=1.0)
    failed = [check.name for check in score.checks if not check.passed]
    assert failed == ["line_items[1].description"]
    # amounts on the positionally matched item still pass
    amount_check = next(check for check in score.checks if check.name == "line_items[1].amount")
    assert amount_check.passed is True and amount_check.note == "matched by position"


def test_completeness_counts_expected_non_null_fields_only() -> None:
    expected = {**EXPECTED, "subtotal": None, "tax": None}
    # wanted: vendor, invoice_number, invoice_date, currency, total, line_items = 6 fields
    actual = {**exact_copy(), "subtotal": None, "tax": None, "total": None, "line_items": []}
    assert completeness_score(expected, actual) == pytest.approx(4 / 6)
    assert completeness_score(expected, None) == 0.0
    assert completeness_score(expected, exact_copy()) == 1.0


def test_schema_failure_is_recorded_but_fields_still_scored() -> None:
    actual = exact_copy()
    actual["currency"] = "us dollars"  # violates the 3 letter pattern
    actual["unexpected"] = "field"  # extra fields are forbidden
    score = score_case("schema", EXPECTED, actual, latency_ms=1.0)
    assert score.schema_ok is False
    assert "schema error" in (score.schema_error or "")
    assert score.passed is False
    currency = next(check for check in score.checks if check.name == "currency")
    assert currency.passed is False
    total = next(check for check in score.checks if check.name == "total")
    assert total.passed is True


def test_extraction_error_scores_zero() -> None:
    score = score_case("boom", EXPECTED, None, latency_ms=1.0, error="TimeoutError: upstream")
    assert score.passed is False
    assert score.field_accuracy == 0.0
    assert score.completeness == 0.0
    assert score.checks[0].name == "extraction"
