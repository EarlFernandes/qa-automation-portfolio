import type { Locator } from '@playwright/test';
import { parseMoney } from '../utils/money';

/**
 * One product card in the inventory list or one row in the cart.
 * The card is addressed by product name, so tests read like the UI:
 *   await inventoryPage.product('Sauce Labs Backpack').addToCart();
 */
export class ProductCardComponent {
  readonly name: Locator;
  readonly description: Locator;
  readonly price: Locator;
  readonly addToCartButton: Locator;
  readonly removeButton: Locator;
  /** The title link, exposed with data-test="item-<id>-title-link". */
  readonly detailsLink: Locator;

  constructor(readonly root: Locator) {
    this.name = root.getByTestId('inventory-item-name');
    this.description = root.getByTestId('inventory-item-desc');
    this.price = root.getByTestId('inventory-item-price');
    this.addToCartButton = root.getByRole('button', { name: 'Add to cart' });
    this.removeButton = root.getByRole('button', { name: 'Remove' });
    this.detailsLink = root.getByTestId(/^item-\d+-title-link$/);
  }

  async addToCart(): Promise<void> {
    await this.addToCartButton.click();
  }

  async remove(): Promise<void> {
    await this.removeButton.click();
  }

  async openDetails(): Promise<void> {
    await this.detailsLink.click();
  }

  /** Reads the displayed price as a number, for example 29.99. */
  async priceValue(): Promise<number> {
    return parseMoney(await this.price.innerText());
  }
}
