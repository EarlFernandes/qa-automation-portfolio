"""Reference adapter for an OpenAI model.

Not used by the tests or the default run. It shows how a real model plugs into
the harness: same `extract(text) -> dict` contract, structured output locked to
the `Invoice` JSON schema. Set OPENAI_API_KEY and optionally LLM_EVALS_OPENAI_MODEL.
"""

from __future__ import annotations

import json
import os
from typing import Any

from llm_evals.extractors.base import SYSTEM_PROMPT
from llm_evals.schema import json_schema


class OpenAIExtractor:
    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install the optional dependency: pip install 'llm-evals[openai]'") from exc
        self._client = OpenAI()
        self._model = model or os.environ.get("LLM_EVALS_OPENAI_MODEL", "gpt-4o-mini")
        self.name = f"openai:{self._model}"

    def extract(self, text: str) -> dict[str, Any]:
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "invoice", "schema": json_schema(), "strict": False},
            },
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
