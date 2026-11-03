"""Adapter for an OpenAI model.

Needs OPENAI_API_KEY and the optional dependency: pip install 'llm-evals[openai]'.
The model comes from the --model flag, else the LLM_MODEL variable, else the default.

JSON mode (response_format json_object) keeps the reply a single object. The reply
still goes through parse_json_object, so the two adapters share one parsing path.
Rate limit (429) and connection errors are retried three times with exponential
backoff. Auth errors are not retried.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from llm_evals.extractors._llm_common import (
    ExtractorSetupError,
    build_prompts,
    is_retryable_error,
    parse_json_object,
    require_env,
    usage_tokens,
    with_retries,
)

DEFAULT_MODEL = "gpt-4o-mini"
INSTALL_HINT = "Install the SDK with: pip install 'llm-evals[openai]'"


class OpenAIExtractor:
    name = "openai"

    def __init__(self, model: str | None = None, client: Any | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL
        self.name = f"openai:{self._model}"
        self.last_usage: dict[str, int] | None = None
        self._sleep = sleep
        if client is not None:
            self._client = client
            return
        require_env("OPENAI_API_KEY", INSTALL_HINT)
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ExtractorSetupError(f"the openai package is not installed. {INSTALL_HINT}") from exc
        self._client = OpenAI()

    def extract(self, text: str) -> dict[str, Any]:
        system, user = build_prompts(text)

        def call() -> Any:
            return self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )

        response = with_retries(call, is_retryable_error, sleep=self._sleep)
        self.last_usage = usage_tokens(response, "prompt_tokens", "completion_tokens")
        choices = getattr(response, "choices", None) or []
        content = getattr(getattr(choices[0], "message", None), "content", "") if choices else ""
        return parse_json_object(content or "")
