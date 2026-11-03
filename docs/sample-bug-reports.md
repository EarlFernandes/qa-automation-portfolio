# Sample bug reports

Two findings from building the suites, written the way I file them: problem first, then what was expected, then the evidence. A developer can act on each without a call.

## 1. Menu button test hook sits on a decorative image

**Problem.** On the product list page, the `data-test="open-menu"` attribute is on the burger menu image, not on the button that receives the click. A test that clicks the element with the test hook clicks the image, and the menu does not open reliably.

**Expected.** The test hook is on the interactive element, the `button` with id `react-burger-menu-btn`, so a click on the hooked element always opens the menu.

**Steps.**

1. Sign in as `standard_user`.
2. In the browser console run `document.querySelector('[data-test="open-menu"]').tagName`.
3. You should see `BUTTON`. You see `IMG`.

**Evidence.** The Selenium page object targets `button#react-burger-menu-btn` with a comment explaining the detour (`selenium/pages/inventory_page.py`). The Playwright suite uses `getByRole('button', { name: 'Open Menu' })`.

**Severity.** Low for users, medium for test automation. Every team that automates this page will hit it.

**Suggested fix.** Move the attribute to the button, or add `data-test="open-menu-button"` to the button and keep the image attribute for one release.

## 2. Pages have no top-level heading

**Problem.** The sign-in, product list and cart pages have no `h1` element. Screen reader users have no page title to jump to, and the axe rule `page-has-heading-one` reports it on every page.

**Expected.** Each page has exactly one `h1` that names the page, for example "Products" on the product list.

**Steps.**

1. Open any of the three pages.
2. Run `npm run test:a11y` in `playwright/`, or run the axe browser extension.
3. You should see no `page-has-heading-one` finding. You see one per page.

**Evidence.** `playwright/a11y.baseline.json` lists the finding as a known issue so the ratchet does not fail. The attached axe JSON in the Playwright report has the node references.

**Severity.** Medium. WCAG 2.1 best practice, not a hard failure, but it affects every screen reader user on every page.

**Suggested fix.** Turn the existing "Products" and "Your Cart" titles into `h1` elements and add a visually hidden `h1` on the sign-in page. Then remove the rule from the baseline so the check guards the fix.
