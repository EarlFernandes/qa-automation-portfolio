import { test, expect } from '../src/fixtures/test';

const IMAGE_URL = /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i;

test.describe('Network control', () => {
  test('inventory still works when product images are blocked', { tag: ['@regression'] }, async ({
    page,
    inventoryPage,
  }) => {
    // Blocking images speeds the test up and proves the page does not depend on them.
    const blocked: string[] = [];
    await page.route(IMAGE_URL, async (route) => {
      blocked.push(route.request().url());
      await route.abort();
    });

    await inventoryPage.goto();
    await expect(inventoryPage.items).toHaveCount(6);

    await inventoryPage.product('Sauce Labs Onesie').addToCart();
    await expect(inventoryPage.header.cartBadge).toHaveText('1');

    expect(blocked.length).toBeGreaterThan(0);
    const renderedWidths = await page
      .getByRole('main')
      .getByRole('img')
      .evaluateAll((images) => images.map((image) => (image as HTMLImageElement).naturalWidth));
    expect(renderedWidths.every((width) => width === 0)).toBe(true);
  });

  test('every same-origin asset on the inventory page loads', { tag: ['@regression'] }, async ({
    page,
    inventoryPage,
    baseURL,
  }) => {
    // The host answers deep links such as /inventory.html with a 404 status and the
    // app shell, which the app then renders. That is a hosting choice, not a broken
    // asset, so document responses are left out and only scripts, styles, fonts and
    // images are checked.
    const origin = new URL(baseURL!).origin;
    const failures: string[] = [];
    page.on('response', (response) => {
      const request = response.request();
      if (request.resourceType() === 'document') return;
      if (response.url().startsWith(origin) && response.status() >= 400) {
        failures.push(`${response.status()} ${response.url()}`);
      }
    });
    page.on('requestfailed', (request) => {
      if (request.url().startsWith(origin)) {
        failures.push(`failed ${request.url()} ${request.failure()?.errorText ?? ''}`);
      }
    });

    await inventoryPage.goto();
    await expect(inventoryPage.items).toHaveCount(6);
    await page.waitForLoadState('load');

    expect(failures).toEqual([]);
  });

  test('home page responds with 200 and HTML', { tag: ['@smoke'] }, async ({ request }) => {
    // The request fixture shares the base URL with the browser, so '/' is enough.
    const response = await request.get('/');

    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('text/html');
  });
});
