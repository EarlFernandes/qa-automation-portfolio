import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';
import { parseMoney } from '../utils/money';

export interface OrderTotals {
  readonly itemTotal: number;
  readonly tax: number;
  readonly total: number;
}

/** Step two of checkout: the order summary with prices, tax and total. */
export class CheckoutOverviewPage extends BasePage {
  readonly items: Locator;
  readonly itemPrices: Locator;
  readonly subtotalLabel: Locator;
  readonly taxLabel: Locator;
  readonly totalLabel: Locator;
  readonly finishButton: Locator;
  readonly cancelButton: Locator;

  constructor(page: Page) {
    super(page, '/checkout-step-two.html');
    this.items = page.getByTestId('inventory-item');
    this.itemPrices = this.items.getByTestId('inventory-item-price');
    this.subtotalLabel = page.getByTestId('subtotal-label');
    this.taxLabel = page.getByTestId('tax-label');
    this.totalLabel = page.getByTestId('total-label');
    this.finishButton = page.getByRole('button', { name: 'Finish' });
    this.cancelButton = page.getByRole('button', { name: 'Cancel' });
  }

  /** Reads the three money lines of the summary as numbers. */
  async totals(): Promise<OrderTotals> {
    const [itemTotal, tax, total] = await Promise.all([
      this.subtotalLabel.innerText(),
      this.taxLabel.innerText(),
      this.totalLabel.innerText(),
    ]);
    return { itemTotal: parseMoney(itemTotal), tax: parseMoney(tax), total: parseMoney(total) };
  }

  /** Reads every line item price as a number. */
  async itemPriceValues(): Promise<number[]> {
    const texts = await this.itemPrices.allInnerTexts();
    return texts.map(parseMoney);
  }

  async finish(): Promise<void> {
    await this.finishButton.click();
  }
}
