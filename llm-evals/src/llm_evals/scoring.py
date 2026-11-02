"""Score one extraction against its answer key, and roll scores up into metrics.

Scoring rules
- Strings match after normalization: casefold, punctuation removed, whitespace collapsed.
- Numbers match within 2% relative tolerance or 0.01 absolute, whichever is larger.
- An expected null must come back null. A returned value where the key says null fails.
- Line items are matched by fingerprint (normalized description plus quantity).
  Items that find no fingerprint partner fall back to positional order. Missing and
  extra items each count as one failed check.
- Completeness is the share of expected non-null fields that came back non-null.
- Field accuracy is passed checks divided by all checks.
- A case passes when the output validates against the schema and every check passes.
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import ValidationError

from llm_evals.schema import NUMERIC_FIELDS, SCALAR_FIELDS, Invoice

REL_TOL = 0.02
ABS_TOL = 0.01

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")


@dataclass
class Check:
    name: str
    expected: Any
    actual: Any
    passed: bool
    note: str = ""


@dataclass
class CaseScore:
    case_id: str
    tags: list[str]
    schema_ok: bool
    schema_error: str | None
    checks: list[Check]
    completeness: float
    field_accuracy: float
    latency_ms: float
    passed: bool
    actual: dict[str, Any] | None
    error: str | None = None
    judge_verdict: str | None = None
    judge_reason: str | None = None
    judge_override: bool = False

    def recompute(self) -> None:
        """Recalculate the summary numbers after a check changed (the judge does this)."""
        total = len(self.checks)
        passed = sum(1 for check in self.checks if check.passed)
        self.field_accuracy = passed / total if total else 0.0
        self.passed = self.schema_ok and passed == total and self.error is None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_text(value: Any) -> str:
    text = str(value).casefold()
    text = _PUNCT.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def numbers_close(expected: float, actual: float, rel_tol: float = REL_TOL, abs_tol: float = ABS_TOL) -> bool:
    return abs(float(expected) - float(actual)) <= max(abs_tol, rel_tol * abs(float(expected)))


def values_match(name: str, expected: Any, actual: Any) -> tuple[bool, str]:
    """Compare one field. Returns (passed, note)."""
    if expected is None:
        return (actual is None, "" if actual is None else "expected null")
    if actual is None:
        return (False, "missing")
    if name in NUMERIC_FIELDS:
        if not is_number(actual):
            return (False, f"not a number: {type(actual).__name__}")
        passed = numbers_close(float(expected), float(actual))
        return (passed, "" if passed else f"outside {REL_TOL:.0%} tolerance")
    passed = normalize_text(expected) == normalize_text(actual)
    return (passed, "" if passed else "text differs after normalization")


def fingerprint(item: dict[str, Any]) -> str:
    quantity = item.get("quantity")
    quantity_key = f"{float(quantity):g}" if is_number(quantity) else str(quantity)
    return f"{normalize_text(item.get('description', ''))}|{quantity_key}"


def match_line_items(
    expected_items: list[dict[str, Any]], actual_items: list[dict[str, Any]]
) -> tuple[list[tuple[int, int | None, str]], list[int]]:
    """Pair expected items with actual items.

    Returns (pairs, extra_actual_indexes). Each pair is (expected_index, actual_index or None, method)
    where method is "fingerprint", "position" or "missing".
    """
    pairs: list[tuple[int, int | None, str]] = []
    used_actual: set[int] = set()
    unmatched_expected: list[int] = []

    actual_by_fingerprint: dict[str, list[int]] = {}
    for index, item in enumerate(actual_items):
        actual_by_fingerprint.setdefault(fingerprint(item), []).append(index)

    for index, item in enumerate(expected_items):
        candidates = [i for i in actual_by_fingerprint.get(fingerprint(item), []) if i not in used_actual]
        if candidates:
            used_actual.add(candidates[0])
            pairs.append((index, candidates[0], "fingerprint"))
        else:
            unmatched_expected.append(index)

    remaining_actual = [i for i in range(len(actual_items)) if i not in used_actual]
    for expected_index in unmatched_expected:
        # Positional fallback: the next unmatched actual item, in order.
        if remaining_actual:
            actual_index = remaining_actual.pop(0)
            used_actual.add(actual_index)
            pairs.append((expected_index, actual_index, "position"))
        else:
            pairs.append((expected_index, None, "missing"))

    pairs.sort(key=lambda pair: pair[0])
    extras = [i for i in range(len(actual_items)) if i not in used_actual]
    return pairs, extras


def completeness_score(expected: dict[str, Any], actual: dict[str, Any] | None) -> float:
    """Share of expected non-null fields that the extractor returned non-null."""
    wanted: list[str] = [name for name in SCALAR_FIELDS if expected.get(name) is not None]
    if expected.get("line_items"):
        wanted.append("line_items")
    if not wanted:
        return 1.0
    if actual is None:
        return 0.0
    returned = 0
    for name in wanted:
        value = actual.get(name)
        if name == "line_items":
            returned += 1 if isinstance(value, list) and len(value) > 0 else 0
        else:
            returned += 1 if value is not None else 0
    return returned / len(wanted)


def validate_schema(actual: dict[str, Any] | None) -> tuple[bool, str | None]:
    if not isinstance(actual, dict):
        return (False, "output is not an object")
    try:
        Invoice.model_validate(actual)
        return (True, None)
    except ValidationError as exc:
        errors = exc.errors()
        first = errors[0]
        location = ".".join(str(part) for part in first.get("loc", ()))
        return (False, f"{len(errors)} schema error(s); first: {location}: {first.get('msg')}")


def score_case(
    case_id: str,
    expected: dict[str, Any],
    actual: dict[str, Any] | None,
    latency_ms: float,
    tags: tuple[str, ...] | list[str] = (),
    error: str | None = None,
) -> CaseScore:
    checks: list[Check] = []

    if error is not None or not isinstance(actual, dict):
        checks.append(Check("extraction", "an Invoice object", None, False, error or "no output"))
        return CaseScore(
            case_id=case_id,
            tags=list(tags),
            schema_ok=False,
            schema_error=error or "no output",
            checks=checks,
            completeness=0.0,
            field_accuracy=0.0,
            latency_ms=latency_ms,
            passed=False,
            actual=actual if isinstance(actual, dict) else None,
            error=error or "no output",
        )

    schema_ok, schema_error = validate_schema(actual)

    for name in SCALAR_FIELDS:
        passed, note = values_match(name, expected.get(name), actual.get(name))
        checks.append(Check(name, expected.get(name), actual.get(name), passed, note))

    expected_items = list(expected.get("line_items") or [])
    actual_items_raw = actual.get("line_items")
    actual_items = [item for item in actual_items_raw if isinstance(item, dict)] if isinstance(actual_items_raw, list) else []
    pairs, extras = match_line_items(expected_items, actual_items)
    for expected_index, actual_index, method in pairs:
        prefix = f"line_items[{expected_index}]"
        expected_item = expected_items[expected_index]
        if actual_index is None:
            checks.append(Check(f"{prefix}.present", expected_item.get("description"), None, False, "item missing"))
            continue
        actual_item = actual_items[actual_index]
        for field_name in ("description", "quantity", "unit_price", "amount"):
            passed, note = values_match(field_name, expected_item.get(field_name), actual_item.get(field_name))
            if method == "position" and not note:
                note = "matched by position"
            checks.append(Check(f"{prefix}.{field_name}", expected_item.get(field_name), actual_item.get(field_name), passed, note))
    for actual_index in extras:
        checks.append(
            Check(f"line_items.extra[{actual_index}]", None, actual_items[actual_index].get("description"), False, "unexpected item")
        )

    score = CaseScore(
        case_id=case_id,
        tags=list(tags),
        schema_ok=schema_ok,
        schema_error=schema_error,
        checks=checks,
        completeness=completeness_score(expected, actual),
        field_accuracy=0.0,
        latency_ms=latency_ms,
        passed=False,
        actual=actual,
    )
    score.recompute()
    return score


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(pct / 100 * len(ordered)) - 1))
    return ordered[rank]


def compute_metrics(scores: list[CaseScore]) -> dict[str, float]:
    """Dataset level metrics. These names are the ones gate.yaml refers to."""
    count = len(scores)
    if count == 0:
        return {}
    extracted = [score for score in scores if score.error is None and score.actual]
    return {
        "case_count": float(count),
        "passed_count": float(sum(1 for score in scores if score.passed)),
        "extraction_rate": len(extracted) / count,
        "schema_conformance_rate": sum(1 for score in scores if score.schema_ok) / count,
        "mean_field_accuracy": statistics.fmean(score.field_accuracy for score in scores),
        "mean_completeness": statistics.fmean(score.completeness for score in scores),
        "case_pass_rate": sum(1 for score in scores if score.passed) / count,
        "p95_latency_ms": percentile([score.latency_ms for score in scores], 95),
        "judge_override_rate": sum(1 for score in scores if score.judge_override) / count,
    }
