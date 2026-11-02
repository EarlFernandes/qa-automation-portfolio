"""Generate data/golden.jsonl.

Every case is synthetic. Vendors, numbers and people do not exist. The script keeps
the answer key and the email text in step: the amounts in the text are computed
from the same quantities and prices that go into the key.

Run from the llm-evals folder:

    python data/generate_golden.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

OUT = Path(__file__).with_name("golden.jsonl")

SYMBOL = {"USD": "$", "EUR": "€", "GBP": "£", "CAD": "CA$"}


@dataclass
class Item:
    description: str
    quantity: float
    unit_price: float

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Spec:
    id: str
    vendor: str
    vendor_in_text: str
    vendor_label: str
    number: str
    number_label: str
    date_iso: str
    date_text: str
    date_label: str
    currency: str
    show_symbol: bool
    currency_label: bool
    items: list[Item]
    layout: str  # A, B or C
    tax_rate: float | None
    tax_label: str
    show_subtotal: bool
    total_label: str
    tags: list[str]
    total_in_words: str | None = None
    forwarded: bool = False
    greeting: str = "Hello,"
    intro: str = "Please find your invoice below."
    tax_as_zero_line: bool = False
    extra_lines: list[str] = field(default_factory=list)


def money(spec: Spec, value: float) -> str:
    symbol = SYMBOL[spec.currency] if spec.show_symbol else ""
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def quantity_text(value: float) -> str:
    return f"{value:g}"


def render_items(spec: Spec) -> list[str]:
    lines: list[str] = []
    if spec.layout == "A":
        lines.append("Items:")
        for item in spec.items:
            lines.append(f"- {item.description}   qty {quantity_text(item.quantity)}   @ {money(spec, item.unit_price)}   = {money(spec, item.amount)}")
    elif spec.layout == "B":
        lines.append("Items:")
        for item in spec.items:
            lines.append(f"{quantity_text(item.quantity)} x {item.description} @ {money(spec, item.unit_price)} = {money(spec, item.amount)}")
    else:
        lines.append("| Description | Qty | Unit price | Amount |")
        lines.append("|---|---|---|---|")
        for item in spec.items:
            lines.append(f"| {item.description} | {quantity_text(item.quantity)} | {money(spec, item.unit_price)} | {money(spec, item.amount)} |")
    return lines


def build(spec: Spec) -> dict:
    subtotal = round(sum(item.amount for item in spec.items), 2)
    tax = round(subtotal * spec.tax_rate, 2) if spec.tax_rate is not None else None
    total = round(subtotal + (tax or 0.0), 2)

    body: list[str] = [
        f"Subject: Invoice {spec.number}",
        "",
        spec.greeting,
        "",
        spec.intro,
        "",
        f"{spec.vendor_label}: {spec.vendor_in_text}",
        f"{spec.number_label} {spec.number}" if spec.number_label.endswith("#") else f"{spec.number_label}: {spec.number}",
        f"{spec.date_label}: {spec.date_text}",
    ]
    if spec.currency_label:
        body.append(f"Currency: {spec.currency}")
    body.append("")
    body.extend(render_items(spec))
    body.append("")
    if spec.show_subtotal:
        body.append(f"Subtotal: {money(spec, subtotal)}")
    if tax is not None:
        body.append(f"{spec.tax_label}: {money(spec, tax)}")
    if spec.total_in_words:
        body.append(f"{spec.total_label}: {spec.total_in_words} ({money(spec, total)})")
    else:
        body.append(f"{spec.total_label}: {money(spec, total)}")
    body.extend(spec.extra_lines)
    body.extend(["", "Thank you for your business.", spec.vendor_in_text])

    text = "\n".join(body)
    if spec.forwarded:
        header = [
            "FYI, can you book this one?",
            "",
            "---------- Forwarded message ---------",
            f"From: accounts@{spec.vendor_in_text.split()[0].lower().strip('&')}-billing.example",
            "Date: Thu, 5 Mar 2026 09:12:00 +0000",
            f"Subject: Invoice {spec.number}",
            "To: payables@customer.example",
            "",
        ]
        quoted = "\n".join(("> " + line) if line else ">" for line in body)
        text = "\n".join(header) + "\n" + quoted

    expected = {
        "vendor": spec.vendor,
        "invoice_number": spec.number,
        "invoice_date": spec.date_iso,
        "currency": spec.currency,
        "subtotal": subtotal if spec.show_subtotal else None,
        "tax": tax,
        "total": total,
        "line_items": [
            {"description": item.description, "quantity": item.quantity, "unit_price": item.unit_price, "amount": item.amount}
            for item in spec.items
        ],
    }
    return {"id": spec.id, "tags": spec.tags, "input_text": text, "expected": expected}


SPECS: list[Spec] = [
    Spec(
        id="nw-001", vendor="Northwind Supplies", vendor_in_text="Northwind Supplies", vendor_label="Vendor",
        number="NW-10342", number_label="Invoice number", date_iso="2026-03-14", date_text="2026-03-14", date_label="Invoice date",
        currency="USD", show_symbol=True, currency_label=True,
        items=[Item("Copier paper A4 80 gsm (box)", 10, 24.50), Item("Toner cartridge black", 2, 89.00)],
        layout="A", tax_rate=0.08, tax_label="Tax (8%)", show_subtotal=True, total_label="Total",
        tags=["usd", "layout-a", "currency-label"],
    ),
    Spec(
        id="hb-002", vendor="Harbor Light Bakery Wholesale", vendor_in_text="Harbor Light Bakery Wholesale", vendor_label="Supplier",
        number="HLB-2026-0088", number_label="Invoice #", date_iso="2026-03-02", date_text="March 2, 2026", date_label="Date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Organic bread flour 25 kg sack", 2.5, 38.00), Item("Sea salt flakes 1 kg", 1.5, 12.40), Item("Delivery to store", 1, 15.00)],
        layout="B", tax_rate=0.05, tax_label="Tax (5%)", show_subtotal=True, total_label="Total due",
        tags=["usd", "layout-b", "decimal-quantity"],
    ),
    Spec(
        id="kl-003", vendor="Kestrel Logistics GmbH", vendor_in_text="Kestrel Logistics GmbH", vendor_label="Issued by",
        number="KL/2026/00317", number_label="Invoice number", date_iso="2026-02-27", date_text="27.02.2026", date_label="Date of issue",
        currency="EUR", show_symbol=True, currency_label=False,
        items=[Item("Pallet transport Hamburg to Munich", 3, 410.00), Item("Fuel surcharge", 1, 86.10)],
        layout="C", tax_rate=0.19, tax_label="VAT 19%", show_subtotal=True, total_label="Total",
        tags=["eur", "layout-c", "vat", "eu-date"],
    ),
    Spec(
        id="bm-004", vendor="Bramblewood Media Ltd", vendor_in_text="Bramblewood Media Limited", vendor_label="Billed by",
        number="BMM-7731", number_label="Invoice number", date_iso="2026-03-14", date_text="14 March 2026", date_label="Invoice date",
        currency="GBP", show_symbol=True, currency_label=False,
        items=[Item("Social media campaign management (March)", 1, 1200.00), Item("Stock photography licence pack", 4, 35.00)],
        layout="A", tax_rate=0.20, tax_label="VAT (20%)", show_subtotal=True, total_label="Total due",
        tags=["gbp", "layout-a", "judge", "legal-suffix"],
    ),
    Spec(
        id="mc-005", vendor="Maple Crest Consulting Inc.", vendor_in_text="Maple Crest Consulting Inc.", vendor_label="Vendor",
        number="MCC-0419", number_label="Invoice number", date_iso="2026-04-19", date_text="2026-04-19", date_label="Invoice date",
        currency="CAD", show_symbol=True, currency_label=True,
        items=[Item("Workshop facilitation day", 2, 1500.00), Item("Travel expenses", 1, 212.75)],
        layout="B", tax_rate=0.13, tax_label="HST (13%)", show_subtotal=True, total_label="Total",
        tags=["cad", "layout-b", "currency-label"],
    ),
    Spec(
        id="ao-006", vendor="Aster & Oak Furniture", vendor_in_text="Aster & Oak Furniture", vendor_label="Seller",
        number="AO-2026-115", number_label="Invoice ID", date_iso="2026-01-30", date_text="Jan 30, 2026", date_label="Invoice date",
        currency="CAD", show_symbol=True, currency_label=False,
        items=[Item("Oak dining table 180 cm", 1, 1899.00), Item("Dining chair walnut", 6, 189.00)],
        layout="A", tax_rate=0.05, tax_label="GST (5%)", show_subtotal=True, total_label="Total",
        tags=["cad", "layout-a", "symbol-only", "known-weakness"],
    ),
    Spec(
        id="pt-007", vendor="Pinecone Tooling Inc.", vendor_in_text="Pinecone Tooling Inc.", vendor_label="Vendor",
        number="PT-55021", number_label="Invoice No", date_iso="2026-03-21", date_text="03/21/2026", date_label="Date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Carbide end mill 10 mm", 12, 32.00), Item("Collet set ER32", 1, 145.00), Item("Spring promotion discount", 1, -50.00)],
        layout="A", tax_rate=0.07, tax_label="Sales tax (7%)", show_subtotal=True, total_label="Total",
        tags=["usd", "layout-a", "discount", "known-weakness"],
    ),
    Spec(
        id="sv-008", vendor="Silverline Veterinary Clinic", vendor_in_text="Silverline Veterinary Clinic", vendor_label="Billed by",
        number="SVC-3306", number_label="Invoice number", date_iso="2026-02-11", date_text="11 Feb 2026", date_label="Date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Wellness exam", 1, 85.00), Item("Rabies vaccination", 1, 42.00)],
        layout="B", tax_rate=None, tax_label="", show_subtotal=False, total_label="Amount due",
        tags=["usd", "layout-b", "no-tax", "no-subtotal"],
        intro="Thank you for visiting us. Here is the invoice for today's appointment.",
    ),
    Spec(
        id="qq-009", vendor="Quill & Quire Stationers", vendor_in_text="Quill & Quire Stationers", vendor_label="Vendor",
        number="QQ-20260305-14", number_label="Invoice number", date_iso="2026-03-05", date_text="2026-03-05", date_label="Invoice date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Fountain pen ink 50 ml bottle", 6, 11.50), Item("Dotted notebook A5", 10, 7.25)],
        layout="A", tax_rate=0.08, tax_label="Tax (8%)", show_subtotal=True, total_label="Total",
        tags=["usd", "layout-a", "forwarded", "noisy", "hard"], forwarded=True,
    ),
    Spec(
        id="tm-010", vendor="Tidewater Marine Services", vendor_in_text="Tidewater Marine Services", vendor_label="Vendor",
        number="TMS-1182", number_label="Invoice number", date_iso="2026-04-02", date_text="April 2, 2026", date_label="Invoice date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Hull cleaning 40 ft vessel", 1, 650.00), Item("Zinc anode replacement", 4, 45.00), Item("Bottom paint ablative (gallon)", 2, 210.00)],
        layout="C", tax_rate=None, tax_label="", show_subtotal=True, total_label="Total due",
        tags=["usd", "layout-c", "words-total", "thousands-separator", "hard"],
        total_in_words="One thousand two hundred fifty dollars and 00/100",
    ),
    Spec(
        id="gp-011", vendor="Granite Peak Landscaping LLC", vendor_in_text="Granite Peak Landscaping LLC", vendor_label="Vendor",
        number="GPL-0907", number_label="Inv. No.", date_iso="2026-05-09", date_text="05/09/2026", date_label="Date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Lawn mowing (per visit)", 4, 60.00), Item("Hedge trimming", 2, 85.00), Item("Mulch delivery (cubic yard)", 3, 48.50), Item("Spring cleanup labor (hour)", 5, 55.00)],
        layout="B", tax_rate=0.06, tax_label="Sales tax (6%)", show_subtotal=True, total_label="Total",
        tags=["usd", "layout-b", "four-items", "us-date"],
    ),
    Spec(
        id="lz-012", vendor="Lumen Zero Software", vendor_in_text="Lumen Zero Software", vendor_label="Issued by",
        number="LZ-INV-2026-0303", number_label="Invoice number", date_iso="2026-03-03", date_text="Mar 3, 2026", date_label="Invoice date",
        currency="EUR", show_symbol=False, currency_label=True,
        items=[Item("Team plan annual subscription (25 seats)", 1, 4500.00)],
        layout="A", tax_rate=0.0, tax_label="VAT (reverse charge)", show_subtotal=True, total_label="Total",
        tags=["eur", "layout-a", "single-item", "reverse-charge", "no-symbol"],
    ),
    Spec(
        id="bb-013", vendor="Blue Birch Printing", vendor_in_text="Blue Birch Printing", vendor_label="Supplier",
        number="BBP/2026/0417", number_label="Invoice No.", date_iso="2026-04-17", date_text="2026-04-17", date_label="Invoice date",
        currency="GBP", show_symbol=True, currency_label=False,
        items=[Item("Business cards 400 gsm matt (500)", 2, 48.00), Item("A2 poster full colour", 25, 6.80)],
        layout="C", tax_rate=0.20, tax_label="VAT (20%)", show_subtotal=True, total_label="Total",
        tags=["gbp", "layout-c", "slash-number"],
    ),
    Spec(
        id="rc-014", vendor="Red Canyon Electrical", vendor_in_text="Red Canyon Electrical", vendor_label="Vendor",
        number="RCE-2041", number_label="Invoice number", date_iso="2026-01-15", date_text="January 15, 2026", date_label="Invoice date",
        currency="USD", show_symbol=True, currency_label=False,
        items=[Item("Service call (first hour)", 1, 120.00), Item("Additional labor (hour)", 2.5, 95.00), Item("20 A breaker", 2, 18.75)],
        layout="B", tax_rate=0.0825, tax_label="Sales tax (8.25%)", show_subtotal=True, total_label="Amount due",
        tags=["usd", "layout-b", "amount-due", "decimal-quantity"],
    ),
]


def main() -> None:
    with OUT.open("w", encoding="utf-8") as handle:
        for spec in SPECS:
            handle.write(json.dumps(build(spec), ensure_ascii=False) + "\n")
    print(f"wrote {len(SPECS)} cases to {OUT}")


if __name__ == "__main__":
    main()
