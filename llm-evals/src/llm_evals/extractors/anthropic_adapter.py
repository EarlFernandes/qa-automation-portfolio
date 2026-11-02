"""Reference adapter for an Anthropic model.

Not used by the tests or the default run. Structured output is obtained through
a forced tool call whose input schema is the `Invoice` JSON schema. Set
ANTHROPIC_API_KEY and optionally LLM_EVALS_ANTHROPIC_MODEL.
"""

from __future__ import annotations

import os
from typing import Any

from llm_evals.extractors.base import SYSTEM_PROMPT
from llm_evals.schema import json_schema


class AnthropicExtractor:
    name = "anthropic"

    def __init__(self, model: str | None = None) -> None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install the optional dependency: pip install 'llm-evals[anthropic]'") from exc
        self._client = anthropic.Anthropic()
        self._model = model or os.environ.get("LLM_EVALS_ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self.name = f"anthropic:{self._model}"

    def extract(self, text: str) -> dict[str, Any]:
        tool = {
            "name": "record_invoice",
            "description": "Record the invoice fields found in the email.",
            "input_schema": json_schema(),
        }
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=[tool],
            tool_choice={"type": "tool", "name": "record_invoice"},
            messages=[{"role": "user", "content": text}],
        )
        for block in response.content:
            if getattr(block, "type", "") == "tool_use":
                return dict(block.input)
        raise RuntimeError("the model returned no tool call")
