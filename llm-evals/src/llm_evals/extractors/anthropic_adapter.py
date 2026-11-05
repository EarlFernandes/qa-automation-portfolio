"""Adapter for an Anthropic model.

Needs ANTHROPIC_API_KEY and the optional dependency: pip install 'llm-evals[anthropic]'.
The model comes from the --model flag, else the LLM_MODEL variable, else the default.

The prompt embeds the Invoice JSON schema and asks for JSON only. The reply is parsed
with parse_json_object, so a stray sentence or a code fence does not break the run.
Rate limit, overloaded (529) and connection errors are retried three times with
exponential backoff. Auth errors are not retried.
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
    call_with_optional_temperature,
)

DEFAULT_MODEL = "claude-haiku-4-5"
INSTALL_HINT = "Install the SDK with: pip install 'llm-evals[anthropic]'"


class AnthropicExtractor:
    name = "anthropic"

    def __init__(self, model: str | None = None, client: Any | None = None, sleep: Callable[[float], None] = time.sleep) -> None:
        self._model = model or os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL
        self.name = f"anthropic:{self._model}"
        self.last_usage: dict[str, int] | None = None
        self._sleep = sleep
        if client is not None:
            # Tests inject a fake client. No key and no SDK needed.
            self._client = client
            return
        require_env("ANTHROPIC_API_KEY", INSTALL_HINT)
        try:
            import anthropic
        except ImportError as exc:
            raise ExtractorSetupError(f"the anthropic package is not installed. {INSTALL_HINT}") from exc
        self._client = anthropic.Anthropic()

    def extract(self, text: str) -> dict[str, Any]:
        system, user = build_prompts(text)

        def call() -> Any:
            return call_with_optional_temperature(
                self._client.messages.create,
                model=self._model,
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": user}],
            )

        response = with_retries(call, is_retryable_error, sleep=self._sleep)
        self.last_usage = usage_tokens(response, "input_tokens", "output_tokens")
        return parse_json_object(_first_text(response))


def _first_text(response: Any) -> str:
    """Text of the first text block. Tool or thinking blocks are skipped."""
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", "text") == "text":
            return getattr(block, "text", "") or ""
    return ""
