import re

_MONEY = re.compile(r"-?\d+(?:\.\d+)?")


def parse_money(text: str) -> float:
    """Turn "Item total: $39.98" or "$29.99" into 39.98 or 29.99."""
    match = _MONEY.search(text.replace(",", ""))
    if not match:
        raise ValueError(f"No amount found in: {text!r}")
    return float(match.group())
