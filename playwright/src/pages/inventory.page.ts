import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';
import { ProductCardComponent } from '../components/product-card.component';

export type SortOption = 'az' | 'za' | 'lohi' | 'hilo';

export class InventoryPage extends BasePage {
  readonly items: Locator;
  readonly productNames: Locator;
  readonly productPrices: Locator;
  readonly sortSelect: Locator;

  constructor(page: Page) {
    super(page, '/inventory.html');
    this.items = page.getByTestId('inventory-item');
    this.productNames = this.items.getByTestId('inventory-item-name');
    this.productPrices = this.items.getByTestId('inventory-item-price');
    this.sortSelect = page.getByRole('combobox', { name: 'Sort products' });
  }

  /** Returns the card for one product, matched on its exact name. */
  product(name: string): ProductCardComponent {
    const card = this.items.filter({ has: this.page.getByText(name, { exact: true }) });
    return new ProductCardComponent(card);
  }

  async sortBy(option: SortOption): Promise<void> {
    await this.sortSelect.selectOption(option);
  }

  /** Reads every displayed price as a number, in page order. */
  async priceValues(): Promise<number[]> {
    const texts = await this.productPrices.allInnerTexts();
    return texts.map((text) => Number(text.replace('$', '')));
  }
}
