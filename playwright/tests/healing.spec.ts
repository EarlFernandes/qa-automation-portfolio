import { test, expect } from '../src/fixtures/test';
import { healingLocator, readHealingEvents } from '../src/healing/heal';

/**
 * Shows the heal-and-propose flow on purpose. The first test points its primary
 * locator at a test id that does not exist on the page, the way a stale locator
 * looks after a front end change. The fallbacks find the element, the test
 * passes, and a healing event is recorded for review.
 */
test.describe('Self-healing locators', () => {
  test.beforeEach(async ({ inventoryPage }) => {
    await inventoryPage.goto();
  });

  test('stale primary locator heals through a fallback and is reported', { tag: ['@regression'] }, async ({ page, inventoryPage }, testInfo) => {
    const addToCart = await healingLocator(page, {
      name: 'add to cart (backpack)',
      intent: 'add Sauce Labs Backpack to the cart',
      candidates: [
        {
          // Stale on purpose. The site uses add-to-cart-sauce-labs-backpack.
          describe: "getByTestId('add-to-cart-backpack-legacy')",
          build: (p) => p.getByTestId('add-to-cart-backpack-legacy'),
        },
        {
          describe: "getByTestId('inventory-item').filter({ hasText: 'Sauce Labs Backpack' }).getByRole('button', { name: 'Add to cart' })",
          build: (p) =>
            p.getByTestId('inventory-item').filter({ hasText: 'Sauce Labs Backpack' }).getByRole('button', { name: 'Add to cart' }),
        },
        {
          describe: "locator('#add-to-cart-sauce-labs-backpack')",
          build: (p) => p.locator('#add-to-cart-sauce-labs-backpack'),
        },
      ],
    });

    await addToCart.click();
    await expect(inventoryPage.header.cartBadge).toHaveText('1');

    const events = readHealingEvents().filter(
      (event) => event.test === testInfo.title && event.project === testInfo.project.name,
    );
    expect(events.length).toBeGreaterThanOrEqual(1);
    for (const event of events) {
      expect(event.primary).toBe("getByTestId('add-to-cart-backpack-legacy')");
      expect(event.winnerIndex).toBe(1);
      expect(event.winner).toContain("getByRole('button', { name: 'Add to cart' })");
      expect(event.proposal).toContain('Replace');
      expect(event.url).toContain('/inventory.html');
    }
  });

  test('healthy primary locator records no healing event', { tag: ['@regression'] }, async ({ page, inventoryPage }, testInfo) => {
    const addToCart = await healingLocator(page, {
      name: 'add to cart (bike light)',
      intent: 'add Sauce Labs Bike Light to the cart',
      candidates: [
        {
          describe: "getByTestId('add-to-cart-sauce-labs-bike-light')",
          build: (p) => p.getByTestId('add-to-cart-sauce-labs-bike-light'),
        },
        {
          describe: "getByTestId('inventory-item').filter({ hasText: 'Sauce Labs Bike Light' }).getByRole('button', { name: 'Add to cart' })",
          build: (p) =>
            p.getByTestId('inventory-item').filter({ hasText: 'Sauce Labs Bike Light' }).getByRole('button', { name: 'Add to cart' }),
        },
      ],
    });

    await addToCart.click();
    await expect(inventoryPage.header.cartBadge).toHaveText('1');

    const events = readHealingEvents().filter(
      (event) => event.test === testInfo.title && event.project === testInfo.project.name,
    );
    expect(events).toHaveLength(0);
  });

  test('throws a readable error when no candidate matches', { tag: ['@regression'] }, async ({ page }) => {
    await expect(
      healingLocator(page, {
        name: 'missing element',
        intent: 'click something that is not on the page',
        timeout: 300,
        candidates: [
          { describe: "getByTestId('does-not-exist')", build: (p) => p.getByTestId('does-not-exist') },
          { describe: "getByRole('button', { name: 'Not a button' })", build: (p) => p.getByRole('button', { name: 'Not a button' }) },
        ],
      }),
    ).rejects.toThrow(/none of 2 candidates attached[\s\S]*primary 0: getByTestId\('does-not-exist'\)[\s\S]*fallback 1/);
  });
});
