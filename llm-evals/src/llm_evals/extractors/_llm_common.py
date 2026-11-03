"""Pieces shared by the model adapters: prompts, JSON parsing, retries, setup errors.

The adapters stay thin. Everything that can be unit tested without a network
lives here, so the tests cover the parsing and retry rules with fake clients.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, TypeVar

from llm_evals.schema import json_schema

T = TypeVar("T")

RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 1.0

# HTTP statuses worth a retry: rate limit and overloaded.
RETRYABLE_STATUSES = frozenset({429, 529})
# Exception class names that mean "try again" across the two SDKs.
RETRYABLE_NAMES = frozenset({"RateLimitError", "APIConnectionError", "APITimeoutError"})
# Exception class names that must never be retried.
FATAL_NAMES = frozenset({"AuthenticationError", "PermissionDeniedError", "BadRequestError", "NotFoundError"})


class ExtractorSetupError(RuntimeError):
    """The extractor cannot start: missing API key or missing SDK package."""


class ModelOutputError(ValueError):
    """The model answered, but not with a usable JSON object."""


SYSTEM_PROMPT_TEMPLATE = """You extract invoice data from the plain text of an email.

Return only one JSON object that matches the JSON schema below. No prose before or after it. No code fences.

Rules:
- Dates as YYYY-MM-DD.
- Numbers as plain JSON numbers, not strings. No currency symbols, no thousands separators.
- currency as a three letter ISO code, for example USD or EUR.
- Use null for a field that is not in the text. Do not guess.
- line_items: one entry per billed line. A discount is a line with a negative amount.
- Copy the vendor name and invoice number as written.

JSON schema:
{schema}
"""


def build_prompts(text: str) -> tuple[str, str]:
    """Return the (system, user) prompts for one email."""
    system = SYSTEM_PROMPT_TEMPLATE.format(schema=json.dumps(json_schema(), indent=2))
    user = f"Email text:\n\n{text}\n\nReturn the JSON object now."
    return system, user


_FENCE = re.compile(r"```[a-zA-Z0-9_-]*")


def parse_json_object(text: str) -> dict[str, Any]:
    """Pull the outermost JSON object out of a model reply.

    Handles code fences, prose before the object and prose after it. Raises
    ModelOutputError with a short preview when there is no usable object.
    """
    if not isinstance(text, str) or not text.strip():
        raise ModelOutputError("the model returned no text")
    cleaned = _FENCE.sub("", text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ModelOutputError(f"no JSON object in the model output: {_preview(text)}")
    candidate = cleaned[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"the model output is not valid JSON ({exc.msg} at position {exc.pos}): {_preview(text)}") from exc
    if not isinstance(data, dict):
        raise ModelOutputError(f"the model output is JSON but not an object: {_preview(text)}")
    return data


def _preview(text: str, limit: int = 120) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "..."


def is_retryable_error(exc: BaseException) -> bool:
    """Decide from the exception itself, without importing either SDK.

    Both SDKs name their errors the same way (RateLimitError, APIConnectionError,
    APIStatusError with a status_code). Auth and bad request errors are final.
    """
    name = type(exc).__name__
    if name in FATAL_NAMES:
        return False
    status = getattr(exc, "status_code", None)
    if status in (401, 403, 400, 404):
        return False
    if name in RETRYABLE_NAMES:
        return True
    return status in RETRYABLE_STATUSES


def with_retries(
    fn: Callable[[], T],
    is_retryable: Callable[[BaseException], bool] = is_retryable_error,
    attempts: int = RETRY_ATTEMPTS,
    base_delay: float = RETRY_BASE_DELAY,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn up to `attempts` times with exponential backoff (1s, 2s, 4s ...).

    Only errors that is_retryable accepts are retried. The last error is raised as is.
    """
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - the predicate decides what is retryable
            if attempt >= attempts or not is_retryable(exc):
                raise
            sleep(base_delay * (2 ** (attempt - 1)))
    raise AssertionError("unreachable")


def require_env(name: str, hint: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ExtractorSetupError(f"{name} is not set. Export it before running with this extractor. {hint}")
    return value


def usage_tokens(response: Any, input_attr: str, output_attr: str) -> dict[str, int] | None:
    """Read token counts from a response when the SDK provides them, else None."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    inp = getattr(usage, input_attr, None)
    out = getattr(usage, output_attr, None)
    if inp is None and out is None:
        return None
    return {"input_tokens": int(inp or 0), "output_tokens": int(out or 0)}
