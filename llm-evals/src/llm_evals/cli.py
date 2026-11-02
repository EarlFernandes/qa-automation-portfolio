"""Command line entry point.

    llm-evals run  --dataset data/golden.jsonl --extractor regex --out reports/
    llm-evals gate --results reports/results.json --config gate.yaml --history reports/gate_history.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_evals import __version__
from llm_evals.dataset import Case, load_cases
from llm_evals.extractors import Extractor, get_extractor
from llm_evals.gate import evaluate, format_table, load_config, load_history, record_run, save_history
from llm_evals.judge import HeuristicJudge, Judge, apply_judge
from llm_evals.report import write_html, write_junit, write_results_json
from llm_evals.scoring import CaseScore, compute_metrics, score_case


def run_case(case: Case, extractor: Extractor, judge: Judge) -> CaseScore:
    started = time.perf_counter()
    actual: dict[str, Any] | None = None
    error: str | None = None
    try:
        actual = extractor.extract(case.input_text)
    except Exception as exc:  # the harness must keep going when one call fails
        error = f"{type(exc).__name__}: {exc}"
    latency_ms = (time.perf_counter() - started) * 1000
    score = score_case(case.id, case.expected, actual, latency_ms, tags=case.tags, error=error)
    if error is None:
        apply_judge(score, judge)
    return score


def run(dataset: Path, extractor_name: str, out_dir: Path, limit: int | None = None, judge: Judge | None = None) -> tuple[dict[str, float], list[CaseScore]]:
    cases = load_cases(dataset)
    if limit:
        cases = cases[:limit]
    extractor = get_extractor(extractor_name)
    judge = judge or HeuristicJudge()
    scores = [run_case(case, extractor, judge) for case in cases]
    metrics = compute_metrics(scores)
    run_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "harness_version": __version__,
        "extractor": extractor.name,
        "judge": judge.name,
        "dataset": str(dataset),
        "case_count": len(cases),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    write_results_json(out_dir / "results.json", run_info, metrics, scores)
    write_junit(out_dir / "junit.xml", run_info, scores)
    write_html(out_dir / "report.html", run_info, metrics, scores)
    return metrics, scores


def _print_run_summary(metrics: dict[str, float], scores: list[CaseScore], out_dir: Path) -> None:
    for score in scores:
        failed = sum(1 for check in score.checks if not check.passed)
        flag = "PASS" if score.passed else "FAIL"
        extra = "" if score.passed else f"  ({failed} failed check(s))"
        print(f"  {flag}  {score.case_id:<10} accuracy {score.field_accuracy:>5.0%}  completeness {score.completeness:>5.0%}{extra}")
    print()
    print(f"cases: {int(metrics['passed_count'])}/{int(metrics['case_count'])} passed")
    for name in ("extraction_rate", "schema_conformance_rate", "mean_field_accuracy", "mean_completeness", "case_pass_rate", "judge_override_rate"):
        print(f"{name}: {metrics[name]:.3f}")
    print(f"p95_latency_ms: {metrics['p95_latency_ms']:.0f}")
    print(f"reports: {out_dir / 'report.html'}, {out_dir / 'results.json'}, {out_dir / 'junit.xml'}")


def cmd_run(args: argparse.Namespace) -> int:
    metrics, scores = run(Path(args.dataset), args.extractor, Path(args.out), limit=args.limit)
    _print_run_summary(metrics, scores, Path(args.out))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    metrics = results.get("metrics") or {}
    rules = load_config(args.config)
    history = load_history(args.history)
    outcomes, exit_code = evaluate(metrics, rules, history)
    print(format_table(outcomes))
    print()
    print("gate: " + ("PASS" if exit_code == 0 else "FAIL"))
    if not args.no_record:
        save_history(args.history, record_run(history, outcomes, results.get("run")))
        print(f"recorded run in {args.history}")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm-evals", description="Evaluate an invoice extractor against a golden dataset and gate releases on the result.")
    parser.add_argument("--version", action="version", version=f"llm-evals {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="run the extractor on the dataset and write reports")
    run_parser.add_argument("--dataset", default="data/golden.jsonl")
    run_parser.add_argument("--extractor", default="regex", choices=["regex", "openai", "anthropic"])
    run_parser.add_argument("--out", default="reports")
    run_parser.add_argument("--limit", type=int, default=None, help="only run the first N cases")
    run_parser.set_defaults(func=cmd_run)

    gate_parser = sub.add_parser("gate", help="compare the metrics of a run with gate.yaml")
    gate_parser.add_argument("--results", default="reports/results.json")
    gate_parser.add_argument("--config", default="gate.yaml")
    gate_parser.add_argument("--history", default="reports/gate_history.json")
    gate_parser.add_argument("--no-record", action="store_true", help="evaluate without adding this run to the history")
    gate_parser.set_defaults(func=cmd_gate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
