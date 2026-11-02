"""Tests for the release gate and its promotion policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_evals.gate import (
    HISTORY_LIMIT,
    MetricRule,
    evaluate,
    format_table,
    load_config,
    load_history,
    record_run,
    save_history,
)

RULES = [
    MetricRule("extraction_rate", 0.9, ">=", "blocking"),
    MetricRule("p95_latency_ms", 5000, "<=", "blocking"),
    MetricRule("case_pass_rate", 0.85, ">=", "candidate"),
    MetricRule("judge_override_rate", 0.2, "<=", "warn"),
]


def test_blocking_failure_fails_the_gate() -> None:
    outcomes, exit_code = evaluate({"extraction_rate": 0.5, "p95_latency_ms": 100, "case_pass_rate": 1.0, "judge_override_rate": 0.0}, RULES, [])
    assert exit_code == 1
    assert {o.name: o.status for o in outcomes}["extraction_rate"] == "FAIL"


def test_latency_uses_less_than_or_equal() -> None:
    _, ok = evaluate({"extraction_rate": 1.0, "p95_latency_ms": 5000, "case_pass_rate": 1.0, "judge_override_rate": 0.0}, RULES, [])
    _, too_slow = evaluate({"extraction_rate": 1.0, "p95_latency_ms": 5001, "case_pass_rate": 1.0, "judge_override_rate": 0.0}, RULES, [])
    assert ok == 0 and too_slow == 1


def test_warn_metric_never_fails_the_gate() -> None:
    outcomes, exit_code = evaluate({"extraction_rate": 1.0, "p95_latency_ms": 1, "case_pass_rate": 1.0, "judge_override_rate": 0.9}, RULES, [])
    assert exit_code == 0
    assert {o.name: o.status for o in outcomes}["judge_override_rate"] == "WARN"


def test_missing_metric_is_a_failure_for_blocking_rules() -> None:
    outcomes, exit_code = evaluate({"p95_latency_ms": 1, "case_pass_rate": 1.0}, RULES, [])
    statuses = {o.name: o.status for o in outcomes}
    assert exit_code == 1
    assert statuses["extraction_rate"] == "FAIL"
    assert statuses["judge_override_rate"] == "WARN"


def test_candidate_is_promoted_after_two_consecutive_passes(tmp_path: Path) -> None:
    history_path = tmp_path / "history.json"
    good = {"extraction_rate": 1.0, "p95_latency_ms": 1, "case_pass_rate": 0.9, "judge_override_rate": 0.0}
    bad = {**good, "case_pass_rate": 0.5}

    # Run 1: candidate fails. No history yet, so it only warns.
    history = load_history(history_path)
    outcomes, exit_code = evaluate(bad, RULES, history)
    assert exit_code == 0
    assert {o.name: o.status for o in outcomes}["case_pass_rate"] == "WARN"
    save_history(history_path, record_run(history, outcomes))

    # Runs 2 and 3: candidate passes twice in a row.
    for _ in range(2):
        history = load_history(history_path)
        outcomes, exit_code = evaluate(good, RULES, history)
        assert exit_code == 0
        save_history(history_path, record_run(history, outcomes))

    # Run 4: promoted. A failure now blocks.
    history = load_history(history_path)
    outcomes, exit_code = evaluate(bad, RULES, history)
    candidate = next(o for o in outcomes if o.name == "case_pass_rate")
    assert candidate.effective_blocking is True
    assert candidate.consecutive_passes == 2
    assert candidate.status == "FAIL"
    assert exit_code == 1
    save_history(history_path, record_run(history, outcomes))

    # Run 5: the failure broke the streak, so the metric is back on probation.
    history = load_history(history_path)
    outcomes, exit_code = evaluate(bad, RULES, history)
    candidate = next(o for o in outcomes if o.name == "case_pass_rate")
    assert candidate.effective_blocking is False
    assert candidate.status == "WARN"
    assert exit_code == 0


def test_history_is_trimmed(tmp_path: Path) -> None:
    history_path = tmp_path / "history.json"
    history: list[dict] = []
    for _ in range(HISTORY_LIMIT + 5):
        outcomes, _ = evaluate({"extraction_rate": 1.0, "p95_latency_ms": 1, "case_pass_rate": 1.0, "judge_override_rate": 0.0}, RULES, history)
        history = record_run(history, outcomes)
    save_history(history_path, history)
    assert len(load_history(history_path)) == HISTORY_LIMIT


def test_load_config_rejects_bad_mode(tmp_path: Path) -> None:
    config = tmp_path / "gate.yaml"
    config.write_text("metrics:\n  extraction_rate:\n    threshold: 0.9\n    mode: sometimes\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown mode"):
        load_config(config)


def test_shipped_config_loads_and_table_renders() -> None:
    rules = load_config(Path(__file__).resolve().parents[1] / "gate.yaml")
    assert {rule.name for rule in rules} >= {"extraction_rate", "case_pass_rate", "p95_latency_ms"}
    outcomes, _ = evaluate({rule.name: 1.0 if rule.comparison == ">=" else 0.0 for rule in rules}, rules, [])
    table = format_table(outcomes)
    assert "Metric" in table and "PASS" in table
