import { test as base, expect } from '@playwright/test';
import {
  CartPage,
  CheckoutCompletePage,
  CheckoutInformationPage,
  CheckoutOverviewPage,
  InventoryPage,
  LoginPage,
  ProductDetailsPage,
} from '../pages';
import { users, type Users } from '../data/users';

/**
 * Test fixtures. Every spec imports `test` and `expect` from this file.
 *
 * Page objects are created per test from the `page` fixture, so a test asks for
 * the pages it needs by name and never constructs them by hand:
 *
 *   test('adds to cart', async ({ inventoryPage }) => { ... });
 */
export interface PageFixtures {
  loginPage: LoginPage;
  inventoryPage: InventoryPage;
  productDetailsPage: ProductDetailsPage;
  cartPage: CartPage;
  checkoutInformationPage: CheckoutInformationPage;
  checkoutOverviewPage: CheckoutOverviewPage;
  checkoutCompletePage: CheckoutCompletePage;
  /** The public demo accounts. */
  users: Users;
}

export const test = base.extend<PageFixtures>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
  inventoryPage: async ({ page }, use) => {
    await use(new InventoryPage(page));
  },
  productDetailsPage: async ({ page }, use) => {
    await use(new ProductDetailsPage(page));
  },
  cartPage: async ({ page }, use) => {
    await use(new CartPage(page));
  },
  checkoutInformationPage: async ({ page }, use) => {
    await use(new CheckoutInformationPage(page));
  },
  checkoutOverviewPage: async ({ page }, use) => {
    await use(new CheckoutOverviewPage(page));
  },
  checkoutCompletePage: async ({ page }, use) => {
    await use(new CheckoutCompletePage(page));
  },
  // eslint-disable-next-line no-empty-pattern
  users: async ({}, use) => {
    await use(users);
  },
});

/** A storage state with no cookies. Use it in specs that must start signed out. */
export const signedOutState = { cookies: [], origins: [] };

export { expect };
