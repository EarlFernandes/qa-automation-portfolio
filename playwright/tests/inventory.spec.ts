import { test, expect } from '../src/fixtures/test';
import { formatMoney } from '../src/utils/money';

test.describe('Inventory', () => {
  test.beforeEach(async ({ inventoryPage }) => {
    await inventoryPage.goto();
    await expect(inventoryPage.title).toHaveText('Products');
  });

  test('lists six products with a positive price each', { tag: ['@smoke'] }, async ({ inventoryPage }) => {
    await expect(inventoryPage.items).toHaveCount(6);

    const prices = await inventoryPage.priceValues();
    expect(prices).toHaveLength(6);
    for (const price of prices) {
      expect(price).toBeGreaterThan(0);
    }
  });

  test('products are sorted by name A to Z by default', { tag: ['@regression'] }, async ({ inventoryPage }) => {
    const names = await inventoryPage.productNames.allInnerTexts();
    const sorted = [...names].sort((a, b) => a.localeCompare(b));

    await expect(inventoryPage.sortSelect).toHaveValue('az');
    await expect(inventoryPage.productNames).toHaveText(sorted);
  });

  test('sorts products by name Z to A', { tag: ['@regression'] }, async ({ inventoryPage }) => {
    const names = await inventoryPage.productNames.allInnerTexts();
    const expected = [...names].sort((a, b) => b.localeCompare(a));

    await inventoryPage.sortBy('za');

    // toHaveText with an array waits until the whole list matches, in order.
    await expect(inventoryPage.productNames).toHaveText(expected);
  });

  test('sorts products by price low to high', { tag: ['@regression'] }, async ({ inventoryPage }) => {
    await inventoryPage.sortBy('lohi');

    await expect(inventoryPage.sortSelect).toHaveValue('lohi');
    await expect(async () => {
      const prices = await inventoryPage.priceValues();
      expect(prices).toEqual([...prices].sort((a, b) => a - b));
    }).toPass();
  });

  test('sorts products by price high to low', { tag: ['@regression'] }, async ({ inventoryPage }) => {
    await inventoryPage.sortBy('hilo');

    await expect(inventoryPage.sortSelect).toHaveValue('hilo');
    await expect(async () => {
      const prices = await inventoryPage.priceValues();
      expect(prices).toEqual([...prices].sort((a, b) => b - a));
    }).toPass();
  });

  test('add and remove update the cart badge', { tag: ['@smoke'] }, async ({ inventoryPage }) => {
    const { header } = inventoryPage;
    const backpack = inventoryPage.product('Sauce Labs Backpack');
    const bikeLight = inventoryPage.product('Sauce Labs Bike Light');

    await backpack.addToCart();
    await expect(backpack.removeButton).toBeVisible();
    await expect(header.cartBadge).toHaveText('1');
    await expect(header.cartLink).toHaveAccessibleName('Cart, 1 items');

    await bikeLight.addToCart();
    await expect(header.cartBadge).toHaveText('2');

    await backpack.remove();
    await expect(backpack.addToCartButton).toBeVisible();
    await expect(header.cartBadge).toHaveText('1');

    await bikeLight.remove();
    await expect(header.cartBadge).toBeHidden();
    await expect(header.cartLink).toHaveAccessibleName('Cart, empty');
  });

  test('opens product details from the product name', { tag: ['@regression'] }, async ({
    page,
    inventoryPage,
    productDetailsPage,
  }) => {
    const card = inventoryPage.product('Sauce Labs Fleece Jacket');
    const listedPrice = await card.priceValue();

    await card.openDetails();

    await expect(page).toHaveURL(/\/inventory-item\.html\?id=\d+$/);
    await expect(productDetailsPage.name).toHaveText('Sauce Labs Fleece Jacket');
    await expect(productDetailsPage.price).toHaveText(formatMoney(listedPrice));
    await expect(productDetailsPage.image).toHaveAccessibleName('Sauce Labs Fleece Jacket');

    await productDetailsPage.backToProductsButton.click();
    await expect(inventoryPage.title).toHaveText('Products');
  });

  test('logout returns to the login page', { tag: ['@regression'] }, async ({ page, inventoryPage, loginPage }) => {
    await inventoryPage.header.logout();

    await expect(page).toHaveURL('/');
    await expect(loginPage.form).toBeVisible();
  });
});
