"""Write the run results in three forms.

- results.json: everything, for the gate command and for anyone who wants to query it.
- junit.xml: one test case per golden case, so CI dashboards show the run like a test suite.
- report.html: a self-contained page with summary cards, a case table and expandable diffs.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

from llm_evals.scoring import CaseScore

METRIC_LABELS = {
    "case_pass_rate": "Cases passed",
    "extraction_rate": "Extraction rate",
    "schema_conformance_rate": "Schema conformance",
    "mean_field_accuracy": "Field accuracy",
    "mean_completeness": "Completeness",
    "p95_latency_ms": "p95 latency",
    "judge_override_rate": "Judge overrides",
}


def write_results_json(path: Path, run_info: dict[str, Any], metrics: dict[str, float], scores: list[CaseScore]) -> None:
    payload = {"run": run_info, "metrics": metrics, "cases": [score.to_dict() for score in scores]}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_junit(path: Path, run_info: dict[str, Any], scores: list[CaseScore]) -> None:
    failures = sum(1 for score in scores if not score.passed)
    total_time = sum(score.latency_ms for score in scores) / 1000
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuite name="llm-evals {xml_escape(str(run_info.get("extractor", "")))}" tests="{len(scores)}" '
        f'failures="{failures}" errors="0" time="{total_time:.3f}">',
    ]
    for score in scores:
        lines.append(
            f'  <testcase classname="invoice_extraction" name="{xml_escape(score.case_id)}" time="{score.latency_ms / 1000:.3f}">'
        )
        if not score.passed:
            failed = [check for check in score.checks if not check.passed]
            summary = f"{len(failed)} failed check(s); schema_ok={score.schema_ok}"
            detail = "\n".join(f"{check.name}: expected {check.expected!r}, got {check.actual!r} {check.note}".strip() for check in failed)
            if score.schema_error:
                detail = f"schema: {score.schema_error}\n{detail}"
            lines.append(f'    <failure message="{xml_escape(summary)}">{xml_escape(detail)}</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt_metric(name: str, value: float) -> str:
    if name.endswith("_ms"):
        return f"{value:.0f} ms"
    return f"{value:.1%}"


def _fmt_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


_CSS = """
:root { --ok: #1d7a3e; --bad: #b3261e; --warn: #9a6700; --ink: #1f2328; --muted: #656d76; --line: #d0d7de; --bg: #f6f8fa; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: var(--ink); margin: 0; padding: 24px; max-width: 1100px; margin-inline: auto; }
h1 { font-size: 22px; margin: 0 0 4px; }
.meta { color: var(--muted); font-size: 13px; margin-bottom: 20px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 24px; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; background: var(--bg); }
.card .label { font-size: 12px; color: var(--muted); }
.card .value { font-size: 22px; font-weight: 600; margin-top: 2px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { border-bottom: 1px solid var(--line); padding: 7px 10px; text-align: left; vertical-align: top; }
th { background: var(--bg); font-weight: 600; }
.pass { color: var(--ok); font-weight: 600; }
.fail { color: var(--bad); font-weight: 600; }
.tag { display: inline-block; font-size: 11px; background: #eaeef2; border-radius: 10px; padding: 1px 8px; margin-right: 4px; color: var(--muted); }
details { border: 1px solid var(--line); border-radius: 8px; margin: 10px 0; }
summary { cursor: pointer; padding: 10px 14px; font-weight: 600; }
details > div { padding: 0 14px 14px; }
.checks td.bad { background: #fff1f0; }
pre { background: var(--bg); padding: 10px; border-radius: 6px; overflow: auto; font-size: 12px; }
.note { color: var(--muted); font-size: 12px; }
"""


def write_html(path: Path, run_info: dict[str, Any], metrics: dict[str, float], scores: list[CaseScore]) -> None:
    passed = sum(1 for score in scores if score.passed)
    cards = []
    for name, label in METRIC_LABELS.items():
        if name in metrics:
            cards.append(f'<div class="card"><div class="label">{html.escape(label)}</div><div class="value">{_fmt_metric(name, metrics[name])}</div></div>')

    rows = []
    for score in scores:
        status = '<span class="pass">PASS</span>' if score.passed else '<span class="fail">FAIL</span>'
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in score.tags)
        failed = sum(1 for check in score.checks if not check.passed)
        rows.append(
            f"<tr><td><a href=\"#case-{html.escape(score.case_id)}\">{html.escape(score.case_id)}</a></td><td>{tags}</td>"
            f"<td>{status}</td><td>{score.field_accuracy:.0%}</td><td>{score.completeness:.0%}</td>"
            f"<td>{'yes' if score.schema_ok else 'no'}</td><td>{failed}</td><td>{score.latency_ms:.0f} ms</td></tr>"
        )

    details = []
    for score in scores:
        check_rows = []
        for check in score.checks:
            cls = "" if check.passed else ' class="bad"'
            mark = "ok" if check.passed else "fail"
            check_rows.append(
                f"<tr><td{cls}>{html.escape(check.name)}</td><td{cls}>{html.escape(_fmt_value(check.expected))}</td>"
                f"<td{cls}>{html.escape(_fmt_value(check.actual))}</td><td{cls}>{mark}</td><td{cls} class=\"note\">{html.escape(check.note)}</td></tr>"
            )
        status = "PASS" if score.passed else "FAIL"
        judge = f"{score.judge_verdict or 'n/a'}" + (f" ({html.escape(score.judge_reason)})" if score.judge_reason else "")
        schema = "valid" if score.schema_ok else f"invalid: {html.escape(score.schema_error or '')}"
        details.append(
            f'<details id="case-{html.escape(score.case_id)}"{" open" if not score.passed else ""}>'
            f'<summary>{html.escape(score.case_id)} <span class="{"pass" if score.passed else "fail"}">{status}</span> '
            f'<span class="note">accuracy {score.field_accuracy:.0%}, schema {schema}, judge {judge}</span></summary><div>'
            f'<table class="checks"><tr><th>Check</th><th>Expected</th><th>Actual</th><th>Result</th><th>Note</th></tr>{"".join(check_rows)}</table>'
            f"<p class=\"note\">Raw output</p><pre>{html.escape(json.dumps(score.actual, indent=2, default=str))}</pre></div></details>"
        )

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LLM evals report</title><style>{_CSS}</style></head>
<body>
<h1>Invoice extraction evals</h1>
<div class="meta">extractor <b>{html.escape(str(run_info.get("extractor")))}</b> · dataset <b>{html.escape(str(run_info.get("dataset")))}</b> ·
{passed} of {len(scores)} cases passed · {html.escape(str(run_info.get("timestamp")))}</div>
<div class="cards">{"".join(cards)}</div>
<h2>Cases</h2>
<table><tr><th>Case</th><th>Tags</th><th>Status</th><th>Field accuracy</th><th>Completeness</th><th>Schema</th><th>Failed checks</th><th>Latency</th></tr>
{"".join(rows)}</table>
<h2>Details</h2>
<p class="note">Failed cases are expanded. Each row is one check: expected value from the answer key, actual value from the extractor.</p>
{"".join(details)}
</body></html>
"""
    path.write_text(page, encoding="utf-8")
