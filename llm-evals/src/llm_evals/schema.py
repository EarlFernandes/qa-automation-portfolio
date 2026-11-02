"""The target schema for the extraction task.

Every extractor must return a dict that validates against `Invoice`.
Schema conformance is one of the gated metrics, so the schema is strict:
unknown fields are rejected and the currency must be a three letter code.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LineItem(BaseModel):
    """One billed line on the invoice."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    quantity: float
    unit_price: float
    amount: float


class Invoice(BaseModel):
    """The structured result the extractor must produce."""

    model_config = ConfigDict(extra="forbid")

    vendor: str = Field(min_length=1)
    invoice_number: str = Field(min_length=1)
    invoice_date: str = Field(description="ISO date, YYYY-MM-DD")
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    subtotal: float | None = None
    tax: float | None = None
    total: float
    line_items: list[LineItem] = Field(default_factory=list)

    @field_validator("invoice_date")
    @classmethod
    def _must_be_iso_date(cls, value: str) -> str:
        # date.fromisoformat raises ValueError for anything that is not YYYY-MM-DD.
        date.fromisoformat(value)
        return value


SCALAR_FIELDS: tuple[str, ...] = (
    "vendor",
    "invoice_number",
    "invoice_date",
    "currency",
    "subtotal",
    "tax",
    "total",
)

NUMERIC_FIELDS: frozenset[str] = frozenset({"subtotal", "tax", "total", "quantity", "unit_price", "amount"})


def json_schema() -> dict[str, Any]:
    """Return the JSON Schema for `Invoice`. Model adapters send this to the model."""
    return Invoice.model_json_schema()
