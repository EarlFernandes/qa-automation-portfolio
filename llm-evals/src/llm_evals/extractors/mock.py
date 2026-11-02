"""A deterministic, offline extractor used as the baseline "model".

It reads labelled invoice emails with regular expressions. It exists so the
harness can run anywhere with no API key, and so the report shows what real
failures look like. It has two known weaknesses on purpose:

1. Discount lines are dropped. A billed line with a negative amount is skipped,
   so invoices with a discount line come back with one line item too few.
2. Every dollar sign is read as USD. "CA$" and "A$" become USD unless the email
   states the currency with a "Currency:" label.

Keep these weaknesses. They are the reason two golden cases fail, which is what
a healthy eval run looks like: the gate stays green while the report still
points at real gaps.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_LINE_FLAGS = re.MULTILINE | re.IGNORECASE

_VENDOR = re.compile(r"^(?:Vendor|Supplier|Billed by|Seller|Issued by)\s*:\s*(.+?)\s*$", _LINE_FLAGS)
_INVOICE_NUMBER = re.compile(
    r"^(?:Invoice\s*(?:number\b|no\b\.?|num\b\.?|#|id\b|ref(?:erence)?\b)|Inv\.?\s*(?:no\b\.?|#))\s*[:#]?\s*(\S+)",
    _LINE_FLAGS,
)
_INVOICE_NUMBER_IN_SUBJECT = re.compile(
    r"^Subject\s*:.*?\bInvoice\s+#?\s*([A-Z0-9][A-Z0-9/-]*\d[A-Z0-9/-]*)", _LINE_FLAGS
)
# The labelled invoice date wins. A bare "Date:" line is the fallback, because
# forwarded emails carry a "Date:" header of their own.
_DATE_PRIMARY = re.compile(r"^(?:Invoice\s+date|Date\s+of\s+issue|Issued(?:\s+on)?)\s*:\s*(.+?)\s*$", _LINE_FLAGS)
_DATE_FALLBACK = re.compile(r"^Date\s*:\s*(.+?)\s*$", _LINE_FLAGS)
_CURRENCY = re.compile(r"^Currency\s*:\s*([A-Za-z]{3})\b", _LINE_FLAGS)
_SUBTOTAL = re.compile(r"^\s*Sub\s*-?\s*total\b[^:\n]*:\s*(.+?)\s*$", _LINE_FLAGS)
_TAX = re.compile(r"^\s*(?:Tax(?:es)?|VAT|Sales\s+tax|GST|HST)\b[^:\n]*:\s*(.+?)\s*$", _LINE_FLAGS)
_TOTAL = re.compile(
    r"^\s*(?:Grand\s+total|Total\s+due|Total\s+amount(?:\s+due)?|Amount\s+due|Balance\s+due|Total)\s*:\s*(.+?)\s*$",
    _LINE_FLAGS,
)

# Three line item layouts are supported.
#   A: - Copier paper A4 (box)   qty 10   @ 24.50   = 245.00
#   B: 2 x Toner cartridge black @ $89.00 = $178.00
#   C: | Toner cartridge black | 2 | 89.00 | 178.00 |
_ITEM_A = re.compile(
    r"^[-*•]\s*(?P<desc>.+?)\s+qty\s*:?\s*(?P<qty>[\d.,]+)\s+(?:@|at)\s*(?P<price>\S+)\s*=\s*(?P<amount>\S+)\s*$",
    re.IGNORECASE,
)
_ITEM_B = re.compile(
    r"^(?P<qty>[\d.,]+)\s*[x×]\s*(?P<desc>.+?)\s+(?:@|at)\s*(?P<price>\S+)\s*=\s*(?P<amount>\S+)\s*$",
    re.IGNORECASE,
)
_ITEM_C = re.compile(
    r"^\|?\s*(?P<desc>[^|]+?)\s*\|\s*(?P<qty>[\d.,]+)\s*\|\s*(?P<price>[^|]+?)\s*\|\s*(?P<amount>[^|]+?)\s*\|?\s*$"
)

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_QUOTE_PREFIX = re.compile(r"^(?:>\s?)+")
_ORDINAL = re.compile(r"(\d)(st|nd|rd|th)\b", re.IGNORECASE)

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%m/%d/%Y",  # slashes are read as US month/day/year
    "%d %B %Y",
    "%d %b %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%Y/%m/%d",
)


def parse_money(raw: str) -> float | None:
    """Read the last number in a string.

    "$1,250.00" -> 1250.0. "-50.00" and "CA$-50.00" -> -50.0. "(50.00)" -> -50.0.
    "one thousand dollars (1,000.00)" -> 1000.0, because the last number wins.
    """
    text = raw.strip()
    numbers = _NUMBER.findall(text)
    if not numbers:
        return None
    last = numbers[-1]
    value = float(last.replace(",", ""))
    minus_before = re.search(r"-\s*[A-Za-z$€£]*\s*" + re.escape(last) + r"(?!\d)", text)
    negative = minus_before is not None
    if text.startswith("(") and text.endswith(")") and len(numbers) == 1:
        negative = True
    return -value if negative else value


def parse_quantity(raw: str) -> float | None:
    numbers = _NUMBER.findall(raw)
    return float(numbers[0].replace(",", "")) if numbers else None


def parse_date(raw: str) -> str:
    """Return an ISO date string. Unknown formats come back as written so the schema check fails visibly."""
    cleaned = _ORDINAL.sub(r"\1", raw).replace(",", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return raw.strip()


def _strip_quotes(text: str) -> str:
    """Remove "> " prefixes left by forwarded or quoted emails."""
    return "\n".join(_QUOTE_PREFIX.sub("", line) for line in text.splitlines())


def _first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _currency(text: str) -> str | None:
    labelled = _first(_CURRENCY, text)
    if labelled:
        return labelled.upper()
    if "€" in text:
        return "EUR"
    if "£" in text:
        return "GBP"
    if "$" in text:
        return "USD"  # known weakness: CA$ and A$ are also read as USD
    return None


def _line_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = _ITEM_A.match(line) or _ITEM_B.match(line) or _ITEM_C.match(line)
        if not match:
            continue
        quantity = parse_quantity(match.group("qty"))
        unit_price = parse_money(match.group("price"))
        amount = parse_money(match.group("amount"))
        if quantity is None or unit_price is None or amount is None:
            continue
        if amount < 0:
            continue  # known weakness: discount lines are dropped
        items.append(
            {
                "description": match.group("desc").strip(" .;"),
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
            }
        )
    return items


class RegexExtractor:
    name = "regex"

    def extract(self, text: str) -> dict[str, Any]:
        text = _strip_quotes(text)
        number = _first(_INVOICE_NUMBER, text) or _first(_INVOICE_NUMBER_IN_SUBJECT, text)
        date_raw = _first(_DATE_PRIMARY, text) or _first(_DATE_FALLBACK, text)
        subtotal_raw = _first(_SUBTOTAL, text)
        tax_raw = _first(_TAX, text)
        total_raw = _first(_TOTAL, text)
        return {
            "vendor": _first(_VENDOR, text),
            "invoice_number": number.rstrip(".,;") if number else None,
            "invoice_date": parse_date(date_raw) if date_raw else None,
            "currency": _currency(text),
            "subtotal": parse_money(subtotal_raw) if subtotal_raw else None,
            "tax": parse_money(tax_raw) if tax_raw else None,
            "total": parse_money(total_raw) if total_raw else None,
            "line_items": _line_items(text),
        }
