"""Load the golden dataset.

The dataset is a JSON Lines file. Each line is one case:

    {"id": "nw-001", "tags": ["usd", "two-items"], "input_text": "...", "expected": {...}}

`expected` is the answer key for that case. The key is validated against the
`Invoice` schema at load time, so a broken key fails fast instead of producing
confusing scores later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_evals.schema import Invoice


@dataclass(frozen=True)
class Case:
    id: str
    input_text: str
    expected: dict[str, Any]
    tags: tuple[str, ...] = field(default_factory=tuple)


def load_cases(path: str | Path) -> list[Case]:
    """Read every case from a JSONL file and validate each answer key."""
    cases: list[Case] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            for key in ("id", "input_text", "expected"):
                if key not in record:
                    raise ValueError(f"{path}:{line_number}: missing field '{key}'")
            if record["id"] in seen:
                raise ValueError(f"{path}:{line_number}: duplicate case id '{record['id']}'")
            seen.add(record["id"])
            # Validate the key. A wrong key is a dataset bug, not an extractor bug.
            Invoice.model_validate(record["expected"])
            cases.append(
                Case(
                    id=record["id"],
                    input_text=record["input_text"],
                    expected=record["expected"],
                    tags=tuple(record.get("tags", [])),
                )
            )
    if not cases:
        raise ValueError(f"{path}: the dataset has no cases")
    return cases
