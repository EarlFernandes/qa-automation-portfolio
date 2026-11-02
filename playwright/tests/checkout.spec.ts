import { test, expect } from '../src/fixtures/test';
import type { CheckoutDetails } from '../src/pages';
import { roundMoney, sumMoney } from '../src/utils/money';

const customer: CheckoutDetails = { firstName: 'Ada', lastName: 'Lovelace', postalCode: 'M5V 2T6' };
const TAX_RATE = 0.08;

test.describe('Checkout', () => {
  test('completes a purchase and shows correct totals', { tag: ['@smoke'] }, async ({
    inventoryPage,
    cartPage,
    checkoutInformationPage,
    checkoutOverviewPage,
    checkoutCompletePage,
  }) => {
    const chosen = ['Sauce Labs Backpack', 'Sauce Labs Bike Light', 'Sauce Labs Bolt T-Shirt'];

    await test.step('add three products to the cart', async () => {
      await inventoryPage.goto();
      for (const name of chosen) {
        await inventoryPage.product(name).addToCart();
      }
      await expect(inventoryPage.header.cartBadge).toHaveText(String(chosen.length));
    });

    await test.step('open the cart and start checkout', async () => {
      await inventoryPage.header.openCart();
      await expect(cartPage.itemNames).toHaveText(chosen);
      await cartPage.checkout();
    });

    await test.step('enter customer information', async () => {
      await expect(checkoutInformationPage.title).toHaveText('Checkout: Your Information');
      await checkoutInformationPage.submit(customer);
    });

    await test.step('check the order summary math', async () => {
      await expect(checkoutOverviewPage.title).toHaveText('Checkout: Overview');
      await expect(checkoutOverviewPage.items).toHaveCount(chosen.length);

      const prices = await checkoutOverviewPage.itemPriceValues();
      const totals = await checkoutOverviewPage.totals();
      const expectedItemTotal = sumMoney(prices);

      expect(totals.itemTotal).toBeCloseTo(expectedItemTotal, 2);
      expect(totals.tax).toBeCloseTo(roundMoney(expectedItemTotal * TAX_RATE), 2);
      expect(totals.total).toBeCloseTo(roundMoney(totals.itemTotal + totals.tax), 2);
    });

    await test.step('finish the order', async () => {
      await checkoutOverviewPage.finish();
      await expect(checkoutCompletePage.title).toHaveText('Checkout: Complete!');
      await expect(checkoutCompletePage.completeHeader).toHaveText('Thank you for your order!');
      await expect(checkoutCompletePage.header.cartBadge).toBeHidden();

      await checkoutCompletePage.backHomeButton.click();
      await expect(inventoryPage.title).toHaveText('Products');
    });
  });

  test.describe('information form validation', () => {
    test.beforeEach(async ({ inventoryPage, cartPage, checkoutInformationPage }) => {
      await inventoryPage.goto();
      await inventoryPage.product('Sauce Labs Onesie').addToCart();
      await inventoryPage.header.openCart();
      await cartPage.checkout();
      await expect(checkoutInformationPage.title).toHaveText('Checkout: Your Information');
    });

    test('requires a first name', { tag: ['@regression'] }, async ({ checkoutInformationPage }) => {
      await checkoutInformationPage.submit({ ...customer, firstName: '' });

      await expect(checkoutInformationPage.errorMessage).toContainText('First Name is required');
    });

    test('requires a last name', { tag: ['@regression'] }, async ({ checkoutInformationPage }) => {
      await checkoutInformationPage.submit({ ...customer, lastName: '' });

      await expect(checkoutInformationPage.errorMessage).toContainText('Last Name is required');
    });

    test('requires a postal code', { tag: ['@regression'] }, async ({ checkoutInformationPage }) => {
      await checkoutInformationPage.submit({ ...customer, postalCode: '' });

      await expect(checkoutInformationPage.errorMessage).toContainText('Postal Code is required');
    });

    test('cancel returns to the cart with the item still in it', { tag: ['@regression'] }, async ({
      checkoutInformationPage,
      cartPage,
    }) => {
      await checkoutInformationPage.cancelButton.click();

      await expect(cartPage.title).toHaveText('Your Cart');
      await expect(cartPage.itemNames).toHaveText(['Sauce Labs Onesie']);
    });
  });
});
