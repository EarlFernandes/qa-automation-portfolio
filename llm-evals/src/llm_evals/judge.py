"""Second opinion on fields where exact matching is too strict.

Vendor names are the example: "Bramblewood Media Ltd" and "Bramblewood Media Limited"
are the same vendor. The deterministic check fails, so a judge gets asked. The
judge can turn that one check into a pass. Every override is recorded on the case
and counted in the `judge_override_rate` metric, so a judge that says yes too often
is visible in the gate table.

`HeuristicJudge` runs offline. `LLMJudge` is the reference for a model based judge.
"""

from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from typing import Protocol

from llm_evals.scoring import CaseScore, normalize_text


@dataclass(frozen=True)
class Verdict:
    equivalent: bool
    reason: str


class Judge(Protocol):
    name: str

    def judge_vendor(self, expected: str, actual: str) -> Verdict: ...


class HeuristicJudge:
    """Similarity ratio on normalized text. 0.85 or more counts as the same vendor."""

    name = "heuristic"
    threshold = 0.85

    def judge_vendor(self, expected: str, actual: str) -> Verdict:
        ratio = difflib.SequenceMatcher(None, normalize_text(expected), normalize_text(actual)).ratio()
        if ratio >= self.threshold:
            return Verdict(True, f"similarity {ratio:.2f} is at or above {self.threshold}")
        return Verdict(False, f"similarity {ratio:.2f} is below {self.threshold}")


RUBRIC = (
    "You compare two vendor names taken from invoices. Answer EQUIVALENT when both names "
    "refer to the same company, allowing for legal suffixes (Ltd, Limited, Inc, GmbH), "
    "punctuation and casing. Answer DIFFERENT otherwise. Reply with one word, then one short reason."
)


class LLMJudge:
    """Reference implementation of a model based judge. Needs OPENAI_API_KEY."""

    name = "llm"

    def __init__(self, model: str | None = None) -> None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        from openai import OpenAI  # optional dependency

        self._client = OpenAI()
        self._model = model or os.environ.get("LLM_EVALS_JUDGE_MODEL", "gpt-4o-mini")

    def judge_vendor(self, expected: str, actual: str) -> Verdict:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": RUBRIC},
                {"role": "user", "content": f"Expected: {expected}\nActual: {actual}"},
            ],
        )
        answer = (response.choices[0].message.content or "").strip()
        return Verdict(answer.upper().startswith("EQUIVALENT"), answer)


def apply_judge(score: CaseScore, judge: Judge) -> None:
    """Ask the judge about the vendor field when the exact check failed. Mutates the score."""
    vendor_check = next((check for check in score.checks if check.name == "vendor"), None)
    if vendor_check is None:
        return
    if vendor_check.passed:
        score.judge_verdict = "not needed"
        score.judge_reason = "exact match"
        return
    if not isinstance(vendor_check.expected, str) or not isinstance(vendor_check.actual, str):
        score.judge_verdict = "skipped"
        score.judge_reason = "vendor missing or not text"
        return
    verdict = judge.judge_vendor(vendor_check.expected, vendor_check.actual)
    score.judge_verdict = "equivalent" if verdict.equivalent else "different"
    score.judge_reason = f"{judge.name}: {verdict.reason}"
    if verdict.equivalent:
        vendor_check.passed = True
        vendor_check.note = f"passed by judge ({judge.name})"
        score.judge_override = True
        score.recompute()
