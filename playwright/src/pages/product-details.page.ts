import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';

export class ProductDetailsPage extends BasePage {
  /** The single product container on this page. */
  readonly root: Locator;
  readonly name: Locator;
  readonly description: Locator;
  readonly price: Locator;
  readonly image: Locator;
  readonly addToCartButton: Locator;
  readonly removeButton: Locator;
  readonly backToProductsButton: Locator;

  constructor(page: Page) {
    super(page, '/inventory-item.html');
    // The details page reuses the "inventory-item" test id of the product list, and the
    // list can still be in the DOM for a moment while the app swaps routes. Only the
    // details container holds the plain "add-to-cart" or "remove" button (the list
    // buttons carry a product suffix), so filtering on it keeps every locator unique.
    const detailsButtons = page.getByTestId('add-to-cart').or(page.getByTestId('remove'));
    this.root = page.getByTestId('inventory-item').filter({ has: detailsButtons });
    this.name = this.root.getByTestId('inventory-item-name');
    this.description = this.root.getByTestId('inventory-item-desc');
    this.price = this.root.getByTestId('inventory-item-price');
    this.image = this.root.getByRole('img');
    this.addToCartButton = this.root.getByRole('button', { name: 'Add to cart' });
    this.removeButton = this.root.getByRole('button', { name: 'Remove' });
    this.backToProductsButton = page.getByRole('button', { name: 'Back to products' });
  }

  /** Opens the details page for a product id, for example 4 for the backpack. */
  async gotoProduct(id: number): Promise<void> {
    await this.page.goto(`${this.path}?id=${id}`);
  }
}
