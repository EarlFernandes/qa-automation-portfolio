import type { Locator, Page } from '@playwright/test';
import { BasePage } from './base.page';
import type { User } from '../data/users';

export class LoginPage extends BasePage {
  readonly form: Locator;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly loginButton: Locator;
  /** The red error banner. The site renders it with data-test="error". */
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page, '/');
    this.form = page.getByRole('form', { name: 'Login' });
    this.usernameInput = this.form.getByRole('textbox', { name: 'Username' });
    this.passwordInput = this.form.getByRole('textbox', { name: 'Password' });
    this.loginButton = this.form.getByRole('button', { name: 'Login' });
    this.errorMessage = page.getByTestId('error');
  }

  async login(user: User): Promise<void> {
    await this.loginWith(user.username, user.password);
  }

  /** Low level variant for negative tests that need odd or empty values. */
  async loginWith(username: string, password: string): Promise<void> {
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.loginButton.click();
  }
}
