import fs from 'node:fs';
import path from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';
import { test, expect, signedOutState } from '../src/fixtures/test';

/**
 * Accessibility scans with axe-core.
 *
 * Two rules decide the outcome:
 * 1. A finding with impact "critical" fails the test. No exceptions.
 * 2. Every other finding must be listed in a11y.baseline.json for that page.
 *    A rule id that is not in the baseline fails the test. This is a ratchet:
 *    known issues stay visible and documented, new issues cannot slip in, and
 *    a fixed issue is removed from the baseline so it cannot come back.
 *
 * The full axe result is attached to every test, so the HTML report holds the
 * nodes and the fix guidance for each finding.
 */
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'];

type Baseline = Record<string, Record<string, string>>;
const baseline = JSON.parse(fs.readFileSync(path.join(__dirname, '../a11y.baseline.json'), 'utf8')) as Baseline;

async function scan(page: Page, pageKey: string) {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  await test.info().attach(`axe-${pageKey}.json`, {
    body: JSON.stringify(results, null, 2),
    contentType: 'application/json',
  });

  const counts: Record<string, number> = {};
  for (const violation of results.violations) {
    const impact = violation.impact ?? 'unknown';
    counts[impact] = (counts[impact] ?? 0) + 1;
  }
  console.log(`[a11y] ${pageKey}: ${results.violations.length} rule(s) failed`, counts, `(${results.passes.length} rules passed)`);

  const critical = results.violations.filter((v) => v.impact === 'critical').map((v) => `${v.id}: ${v.help}`);
  expect(critical, 'critical accessibility findings').toEqual([]);

  const known = baseline[pageKey] ?? {};
  const unexpected = results.violations
    .filter((v) => !(v.id in known))
    .map((v) => `${v.id} (${v.impact}): ${v.help}. ${v.nodes.length} node(s). Fix help: ${v.helpUrl}`);
  expect(unexpected, 'findings that are not in a11y.baseline.json').toEqual([]);

  // The other direction: a baseline entry that no longer fires should be removed.
  const stale = Object.keys(known).filter((id) => !results.violations.some((v) => v.id === id));
  expect(stale, 'baseline entries the site no longer triggers, remove them').toEqual([]);
}

test.describe('Accessibility', () => {
  test.describe('signed out', () => {
    test.use({ storageState: signedOutState });

    test('login page has no critical findings and no new findings', { tag: ['@a11y'] }, async ({ page, loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.loginButton).toBeVisible();
      await scan(page, 'login');
    });
  });

  test('inventory page has no critical findings and no new findings', { tag: ['@a11y'] }, async ({ page, inventoryPage }) => {
    await inventoryPage.goto();
    await expect(inventoryPage.items).toHaveCount(6);
    await scan(page, 'inventory');
  });

  test('cart page has no critical findings and no new findings', { tag: ['@a11y'] }, async ({ page, inventoryPage, cartPage }) => {
    await inventoryPage.goto();
    await inventoryPage.product('Sauce Labs Backpack').addToCart();
    await cartPage.goto();
    await expect(cartPage.items).toHaveCount(1);
    await scan(page, 'cart');
  });
});
