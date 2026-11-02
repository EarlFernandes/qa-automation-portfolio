import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';

/** The confirmation page shown after a finished order. */
export class CheckoutCompletePage extends BasePage {
  readonly completeHeader: Locator;
  readonly completeText: Locator;
  readonly backHomeButton: Locator;

  constructor(page: Page) {
    super(page, '/checkout-complete.html');
    this.completeHeader = page.getByTestId('complete-header');
    this.completeText = page.getByTestId('complete-text');
    this.backHomeButton = page.getByRole('button', { name: 'Back Home' });
  }
}
