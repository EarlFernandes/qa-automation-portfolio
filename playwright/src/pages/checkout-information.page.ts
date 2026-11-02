import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';

export interface CheckoutDetails {
  readonly firstName: string;
  readonly lastName: string;
  readonly postalCode: string;
}

/** Step one of checkout: the customer information form. */
export class CheckoutInformationPage extends BasePage {
  readonly form: Locator;
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly postalCodeInput: Locator;
  readonly continueButton: Locator;
  readonly cancelButton: Locator;
  /** Validation errors are announced through an alert region. */
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page, '/checkout-step-one.html');
    this.form = page.getByRole('form', { name: 'Checkout information' });
    this.firstNameInput = this.form.getByRole('textbox', { name: 'First Name' });
    this.lastNameInput = this.form.getByRole('textbox', { name: 'Last Name' });
    this.postalCodeInput = this.form.getByRole('textbox', { name: 'Zip/Postal Code' });
    this.continueButton = this.form.getByRole('button', { name: 'Continue' });
    this.cancelButton = this.form.getByRole('button', { name: 'Cancel' });
    this.errorMessage = this.form.getByRole('alert');
  }

  async fill(details: Partial<CheckoutDetails>): Promise<void> {
    if (details.firstName !== undefined) await this.firstNameInput.fill(details.firstName);
    if (details.lastName !== undefined) await this.lastNameInput.fill(details.lastName);
    if (details.postalCode !== undefined) await this.postalCodeInput.fill(details.postalCode);
  }

  async continue(): Promise<void> {
    await this.continueButton.click();
  }

  async submit(details: CheckoutDetails): Promise<void> {
    await this.fill(details);
    await this.continue();
  }
}
