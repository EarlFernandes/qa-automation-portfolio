# Golden dataset

`golden.jsonl` holds 14 synthetic invoice emails and their answer keys. Every vendor, number and amount is invented. `generate_golden.py` writes the file from one list of specifications, so the text and the key always agree.

Each line is one case:

```json
{"id": "nw-001", "tags": ["usd", "layout-a"], "input_text": "...", "expected": {"vendor": "...", "total": 456.84, "line_items": [...]}}
```

## Rules for the answer key

1. Never edit a key to make a run pass. If the extractor disagrees with the key, the extractor is wrong until proven otherwise.
2. Fix a key only when the key itself is wrong, and only when the application behaviour must not change. Record the reason in the commit message and in the case `tags` (for example `key-fix-2026-05`).
3. Never lower a gate threshold to get a green run. Open a ticket for the regression instead.
4. Add a case for every production bug that the harness missed. That is how the dataset grows.
5. Keep the dataset small enough to run on every pull request. Move slow or rare cases to a second file and run it on a schedule.

## Case tags

| Tag | Meaning |
|---|---|
| `layout-a`, `layout-b`, `layout-c` | The line item layout used in the email text. |
| `currency-label` | The email states the currency with a `Currency:` line. |
| `symbol-only` | The currency appears only as a symbol. |
| `discount` | The invoice has a negative line. |
| `no-tax`, `no-subtotal` | The key expects null for that field. |
| `forwarded`, `noisy` | The email is a forwarded message with quoted lines. |
| `words-total` | The total is written in words and digits. |
| `judge` | The vendor name needs the judge to pass. |
| `known-weakness` | The offline regex extractor fails this case on purpose. |
| `hard` | A case that trips simple extractors. |

## Regenerate

```bash
python data/generate_golden.py
```

Review the diff before committing. A changed amount in an existing case is a key change and needs a reason.
