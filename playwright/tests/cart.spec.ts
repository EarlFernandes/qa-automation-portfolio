import { test, expect } from '../src/fixtures/test';
import { formatMoney } from '../src/utils/money';

const BACKPACK = 'Sauce Labs Backpack';
const ONESIE = 'Sauce Labs Onesie';

test.describe('Cart', () => {
  test.beforeEach(async ({ inventoryPage }) => {
    await inventoryPage.goto();
    await expect(inventoryPage.title).toHaveText('Products');
  });

  test('shows the items that were added, with their prices', { tag: ['@smoke'] }, async ({
    inventoryPage,
    cartPage,
  }) => {
    const backpackPrice = await inventoryPage.product(BACKPACK).priceValue();
    await inventoryPage.product(BACKPACK).addToCart();
    await inventoryPage.product(ONESIE).addToCart();

    await inventoryPage.header.openCart();

    await expect(cartPage.title).toHaveText('Your Cart');
    await expect(cartPage.itemNames).toHaveText([BACKPACK, ONESIE]);
    await expect(cartPage.item(BACKPACK).price).toHaveText(formatMoney(backpackPrice));
  });

  test('removes one item and keeps the other', { tag: ['@regression'] }, async ({ inventoryPage, cartPage }) => {
    await inventoryPage.product(BACKPACK).addToCart();
    await inventoryPage.product(ONESIE).addToCart();
    await inventoryPage.header.openCart();

    await cartPage.item(BACKPACK).remove();

    await expect(cartPage.itemNames).toHaveText([ONESIE]);
    await expect(cartPage.header.cartBadge).toHaveText('1');
  });

  test('continue shopping returns to the products and keeps the cart', { tag: ['@regression'] }, async ({
    inventoryPage,
    cartPage,
  }) => {
    await inventoryPage.product(ONESIE).addToCart();
    await inventoryPage.header.openCart();

    await cartPage.continueShopping();

    await expect(inventoryPage.title).toHaveText('Products');
    await expect(inventoryPage.header.cartBadge).toHaveText('1');
    await expect(inventoryPage.product(ONESIE).removeButton).toBeVisible();
  });

  test('cart contents survive a page reload', { tag: ['@regression'] }, async ({ page, inventoryPage, cartPage }) => {
    await inventoryPage.product(BACKPACK).addToCart();
    await inventoryPage.header.openCart();
    await expect(cartPage.itemNames).toHaveText([BACKPACK]);

    await page.reload();

    await expect(cartPage.title).toHaveText('Your Cart');
    await expect(cartPage.itemNames).toHaveText([BACKPACK]);
  });
});
