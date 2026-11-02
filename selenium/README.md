# Selenium suite (Python, Selenium 4, pytest)

Browser tests for the public Swag Labs demo shop at https://www.saucedemo.com.
The suite covers login, product sorting, the cart badge and a full purchase.
It runs headless in about 30 seconds.

The demo site publishes its own test accounts (`standard_user`,
`locked_out_user`, `problem_user`, `performance_glitch_user`, password
`secret_sauce`). They are public demo credentials, not secrets.

## Run it

```bash
cd selenium
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                    # all 13 tests, headless
pytest -m smoke           # the fast checks only
HEADLESS=0 pytest         # watch the browser
```

Selenium Manager downloads a matching chromedriver on first run. Nothing else
to install. Results go to `results/junit.xml`. A failed test saves a
screenshot to `results/screenshots/`.

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `BASE_URL` | `https://www.saucedemo.com` | Target site |
| `HEADLESS` | `1` | Set `0` to show the browser |
| `CHROME_BINARY` | unset | Use a specific Chrome build |
| `CHROMEDRIVER_PATH` | unset | Skip Selenium Manager and use this driver |

## Layout

```
selenium/
├── conftest.py          driver fixture, screenshot on failure, login fixtures
├── pytest.ini           markers (smoke, regression), junit output
├── pages/
│   ├── base_page.py     explicit waits, click retry, by_test_id helper
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── cart_page.py
│   └── checkout_pages.py
├── tests/
│   ├── test_login.py        7 tests (3 users parametrized, lock out, wrong password, empty form, logout)
│   ├── test_inventory.py    4 tests (sorting, relative locator, cart badge)
│   └── test_checkout.py     2 tests (purchase with totals math, validation)
└── utils/money.py       "$29.99" to 29.99
```

## Design choices

Page objects hold locators and actions. Tests hold intent and assertions. A
test never calls `find_element` and never sleeps.

Locator order: the site's `data-test` attribute first, then a stable id, then a
CSS selector. No XPath. One locator in this suite is a Selenium 4 relative
locator (`locate_with(...).below(...)`) that reads the price under a product
name. The test checks it against a plain list read, so the relative locator is
verified, not trusted.

Every page declares `READY_LOCATOR`, one element that proves the page
rendered. `wait_until_loaded()` waits for it. This matters on a single page
app: the URL changes before the new screen has painted, and a test that reads
the DOM at that moment sees nothing.

`BasePage.click()` waits for the element to be clickable, then keeps trying
until the click is accepted. `element_to_be_clickable` only checks visible and
enabled. A menu that is sliding in can still cover the target for a few
frames.

`click_and_wait_for_url()` retries one lost click when a route change does not
happen. The navigation actions here are idempotent, so the retry is safe.

The checkout test does not hard code totals. It reads the line prices and
quantities, sums them, applies the 8 percent tax rate and compares all three
figures against the page.

One browser per test. Slower than a shared session, but no test can leak cart
state into another, and failures reproduce on their own.

Chrome's password manager is switched off in `conftest.py`. Without that, Chrome
opens a "Save password?" bubble about one second after the login form submits.
The bubble takes the input focus, so every later click and key press from the
driver is dropped before it reaches the page, while JavaScript clicks still
work. The symptom was four tests that passed right after login and timed out a
few seconds later, in headless mode and in headed mode under Xvfb alike. Finding
it took three steps: confirm that no mouse event reached the page (a capture
listener on `window` saw nothing), confirm that the same clicks worked through
Playwright, then compare what Playwright turns off that chromedriver leaves on.

## Selenium 4 features used

- Selenium Manager for automatic driver resolution
- Chrome `--headless=new`
- Relative locators (`locate_with`)
- `WebDriverWait` with `expected_conditions` and custom wait predicates

## How this differs from the Playwright suite

The Playwright suite in `../playwright` tests the same site. Playwright has
auto waiting, web first assertions and a built in test runner, so its page
objects are thinner. This suite shows how to get the same stability in
Selenium: explicit waits everywhere, a ready check per page, and a click helper
that handles overlays. Both suites exist because teams run both tools.
