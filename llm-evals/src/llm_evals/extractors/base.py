"""The contract every extractor follows."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Extractor(Protocol):
    """Anything with a `name` and an `extract` method is an extractor.

    `extract` returns a plain dict. The harness validates it against the schema,
    so an extractor does not need to import pydantic. Raise an exception when the
    extraction cannot run at all (network error, bad response). The harness records
    the error as a failed case and continues.
    """

    name: str

    def extract(self, text: str) -> dict[str, Any]: ...


SYSTEM_PROMPT = (
    "You extract invoice data from the plain text of an email. "
    "Return only JSON that matches the given schema. "
    "Use ISO dates (YYYY-MM-DD) and three letter currency codes. "
    "Copy numbers exactly as written. Use null when a value is not in the text. "
    "Include every billed line, including discounts as negative amounts."
)
