"""Run the whole harness on the golden set with the offline extractor."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from llm_evals.cli import main, run
from llm_evals.dataset import load_cases

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "golden.jsonl"
KNOWN_WEAK_CASES = {"ao-006", "pt-007"}


def test_golden_dataset_loads_and_keys_are_valid() -> None:
    cases = load_cases(DATASET)
    assert len(cases) == 14
    assert len({case.id for case in cases}) == 14


def test_regex_extractor_run_matches_the_documented_baseline(tmp_path: Path) -> None:
    metrics, scores = run(DATASET, "regex", tmp_path)

    failed = {score.case_id for score in scores if not score.passed}
    assert failed == KNOWN_WEAK_CASES, f"unexpected failures: {failed ^ KNOWN_WEAK_CASES}"
    assert metrics["extraction_rate"] == 1.0
    assert metrics["schema_conformance_rate"] == 1.0
    assert metrics["case_pass_rate"] == 12 / 14

    # the judge rescued exactly one vendor name (Ltd vs Limited)
    overrides = [score for score in scores if score.judge_override]
    assert [score.case_id for score in overrides] == ["bm-004"]

    for name in ("results.json", "junit.xml", "report.html"):
        assert (tmp_path / name).exists(), name

    results = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert results["run"]["extractor"] == "regex"
    assert len(results["cases"]) == 14

    suite = ET.parse(tmp_path / "junit.xml").getroot()
    assert suite.attrib["tests"] == "14"
    assert suite.attrib["failures"] == "2"

    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "pt-007" in html and "item missing" in html


def test_cli_run_then_gate_passes_with_shipped_thresholds(tmp_path: Path) -> None:
    out = tmp_path / "reports"
    assert main(["run", "--dataset", str(DATASET), "--extractor", "regex", "--out", str(out)]) == 0
    exit_code = main(
        [
            "gate",
            "--results",
            str(out / "results.json"),
            "--config",
            str(ROOT / "gate.yaml"),
            "--history",
            str(tmp_path / "gate_history.json"),
        ]
    )
    assert exit_code == 0
    history = json.loads((tmp_path / "gate_history.json").read_text(encoding="utf-8"))
    assert len(history) == 1
