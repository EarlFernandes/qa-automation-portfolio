import { test, expect, signedOutState } from '../../src/fixtures/test';

/**
 * Visual regression. Runs with `npm run test:visual` (playwright.visual.config.ts).
 *
 * Each check compares the viewport against a committed baseline PNG with a
 * 2 percent pixel budget. Baselines are platform specific, see the README.
 * To refresh them after an intended UI change:
 *   npm run test:visual -- --update-snapshots
 */
test.describe('Visual regression', () => {
  test.describe('signed out', () => {
    test.use({ storageState: signedOutState });

    test('login page matches the baseline', { tag: ['@visual'] }, async ({ page, loginPage }) => {
      await loginPage.goto();
      await expect(loginPage.loginButton).toBeVisible();
      await expect(page).toHaveScreenshot('login-page.png', { fullPage: false });
    });
  });

  test('inventory page matches the baseline', { tag: ['@visual'] }, async ({ page, inventoryPage }) => {
    await inventoryPage.goto();
    await expect(inventoryPage.items).toHaveCount(6);
    // Product images load from the site. Wait until every one has pixels so the baseline is stable.
    const images = inventoryPage.items.locator('img');
    await expect(images).toHaveCount(6);
    await expect
      .poll(() => images.evaluateAll((nodes) => nodes.every((node) => (node as HTMLImageElement).complete && (node as HTMLImageElement).naturalWidth > 0)))
      .toBe(true);
    await expect(page).toHaveScreenshot('inventory-page.png', { fullPage: false });
  });
});
