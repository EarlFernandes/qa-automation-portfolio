import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';
import { ProductCardComponent } from '../components/product-card.component';

export class CartPage extends BasePage {
  readonly items: Locator;
  readonly itemNames: Locator;
  readonly continueShoppingButton: Locator;
  readonly checkoutButton: Locator;

  constructor(page: Page) {
    super(page, '/cart.html');
    this.items = page.getByTestId('inventory-item');
    this.itemNames = this.items.getByTestId('inventory-item-name');
    this.continueShoppingButton = page.getByRole('button', { name: 'Continue Shopping' });
    this.checkoutButton = page.getByRole('button', { name: 'Checkout' });
  }

  /** Returns the cart row for one product, matched on its exact name. */
  item(name: string): ProductCardComponent {
    const row = this.items.filter({ has: this.page.getByText(name, { exact: true }) });
    return new ProductCardComponent(row);
  }

  async continueShopping(): Promise<void> {
    await this.continueShoppingButton.click();
  }

  async checkout(): Promise<void> {
    await this.checkoutButton.click();
  }
}
