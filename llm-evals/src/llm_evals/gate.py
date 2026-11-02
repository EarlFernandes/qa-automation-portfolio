"""The release gate.

The gate reads the metrics of one run and compares them with gate.yaml.
Each metric has a mode:

- blocking: a failure fails the gate (exit code 1).
- warn: a failure is reported as WARN and never fails the gate.
- candidate: a metric on probation. It is treated as warn until it has passed in
  two consecutive recorded runs. From then on it is treated as blocking. This is
  the promotion policy: a new rule has to prove it is stable before it can block
  a release, so a flaky new check cannot stop the team on day one.

Run history lives in a small JSON file (last 20 runs). The gate command records
the current run after it evaluates it, unless --no-record is given.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

MODES = ("blocking", "candidate", "warn")
COMPARISONS = (">=", "<=")
HISTORY_LIMIT = 20
PROMOTION_RUNS = 2


@dataclass(frozen=True)
class MetricRule:
    name: str
    threshold: float
    comparison: str  # ">=" or "<="
    mode: str  # blocking, candidate or warn

    def passes(self, value: float) -> bool:
        return value >= self.threshold if self.comparison == ">=" else value <= self.threshold


@dataclass
class MetricOutcome:
    name: str
    value: float | None
    threshold: float
    comparison: str
    mode: str
    effective_blocking: bool
    consecutive_passes: int
    passed: bool
    status: str  # PASS, FAIL or WARN

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path) -> list[MetricRule]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    metrics = data.get("metrics") or {}
    if not metrics:
        raise ValueError(f"{path}: no metrics defined")
    rules: list[MetricRule] = []
    for name, spec in metrics.items():
        comparison = str(spec.get("comparison", ">="))
        mode = str(spec.get("mode", "blocking"))
        if comparison not in COMPARISONS:
            raise ValueError(f"{path}: metric '{name}' has unknown comparison '{comparison}'")
        if mode not in MODES:
            raise ValueError(f"{path}: metric '{name}' has unknown mode '{mode}'")
        rules.append(MetricRule(name=name, threshold=float(spec["threshold"]), comparison=comparison, mode=mode))
    return rules


def load_history(path: str | Path) -> list[dict[str, Any]]:
    history_path = Path(path)
    if not history_path.exists():
        return []
    data = json.loads(history_path.read_text(encoding="utf-8") or "[]")
    return data if isinstance(data, list) else []


def save_history(path: str | Path, history: list[dict[str, Any]]) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history[-HISTORY_LIMIT:], indent=2), encoding="utf-8")


def consecutive_passes(history: list[dict[str, Any]], metric: str) -> int:
    """How many of the most recent recorded runs passed this metric, counting back until a failure."""
    count = 0
    for run in reversed(history):
        record = (run.get("metrics") or {}).get(metric)
        if not record or not record.get("passed"):
            break
        count += 1
    return count


def evaluate(metrics: dict[str, float], rules: list[MetricRule], history: list[dict[str, Any]]) -> tuple[list[MetricOutcome], int]:
    """Compare metrics with the rules. Returns the outcomes and the exit code (0 or 1)."""
    outcomes: list[MetricOutcome] = []
    exit_code = 0
    for rule in rules:
        value = metrics.get(rule.name)
        streak = consecutive_passes(history, rule.name)
        if rule.mode == "blocking":
            blocking = True
        elif rule.mode == "candidate":
            blocking = streak >= PROMOTION_RUNS
        else:
            blocking = False
        passed = value is not None and rule.passes(value)
        if passed:
            status = "PASS"
        elif blocking:
            status = "FAIL"
            exit_code = 1
        else:
            status = "WARN"
        outcomes.append(
            MetricOutcome(
                name=rule.name,
                value=value,
                threshold=rule.threshold,
                comparison=rule.comparison,
                mode=rule.mode,
                effective_blocking=blocking,
                consecutive_passes=streak,
                passed=passed,
                status=status,
            )
        )
    return outcomes, exit_code


def record_run(history: list[dict[str, Any]], outcomes: list[MetricOutcome], run_info: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run": run_info or {},
        "metrics": {outcome.name: {"value": outcome.value, "passed": outcome.passed} for outcome in outcomes},
    }
    return (history + [entry])[-HISTORY_LIMIT:]


def _mode_label(outcome: MetricOutcome) -> str:
    if outcome.mode == "candidate":
        state = "promoted" if outcome.effective_blocking else f"{min(outcome.consecutive_passes, PROMOTION_RUNS)}/{PROMOTION_RUNS} passes"
        return f"candidate ({state})"
    return outcome.mode


def _format_value(value: float | None, name: str) -> str:
    if value is None:
        return "missing"
    if name.endswith("_ms"):
        return f"{value:.0f} ms"
    if name.endswith("_count"):
        return f"{value:.0f}"
    return f"{value:.3f}"


def format_table(outcomes: list[MetricOutcome]) -> str:
    rows = [("Metric", "Value", "Threshold", "Mode", "Status")]
    for outcome in outcomes:
        threshold = _format_value(outcome.threshold, outcome.name)
        rows.append(
            (
                outcome.name,
                _format_value(outcome.value, outcome.name),
                f"{outcome.comparison} {threshold}",
                _mode_label(outcome),
                outcome.status,
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    lines = []
    for index, row in enumerate(rows):
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if index == 0:
            lines.append("  ".join("-" * widths[i] for i in range(5)))
    return "\n".join(lines)
