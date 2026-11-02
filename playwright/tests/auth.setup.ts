import { test as setup, expect } from '../src/fixtures/test';
import { STORAGE_STATE } from '../playwright.config';

/**
 * Runs once before the browser projects. It signs in through the real login
 * form and saves cookies and local storage to a file. Every later test starts
 * from that file, so the suite pays for one login instead of one per test.
 */
setup('sign in as standard_user and save the browser state', async ({ page, loginPage, inventoryPage, users }) => {
  await loginPage.goto();
  await loginPage.login(users.standard);
  await expect(inventoryPage.title).toHaveText('Products');
  await page.context().storageState({ path: STORAGE_STATE });
});
