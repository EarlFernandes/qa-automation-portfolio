import type { Locator, Page } from '@playwright/test';

/**
 * The header shown on every signed-in page: burger menu, logo and cart link.
 * A component object wraps one reusable part of the UI so that several pages
 * can share it without copying locators.
 */
export class HeaderComponent {
  readonly root: Locator;
  readonly openMenuButton: Locator;
  readonly closeMenuButton: Locator;
  readonly menu: Locator;
  readonly logoutButton: Locator;
  readonly resetAppStateButton: Locator;
  /** The cart link. Its accessible name reads "Cart, empty" or "Cart, N items". */
  readonly cartLink: Locator;
  readonly cartBadge: Locator;

  constructor(private readonly page: Page) {
    this.root = page.getByRole('banner');
    this.openMenuButton = this.root.getByRole('button', { name: 'Open Menu' });
    this.closeMenuButton = page.getByRole('button', { name: 'Close Menu' });
    this.menu = page.getByRole('navigation');
    this.logoutButton = this.menu.getByRole('button', { name: 'Logout' });
    this.resetAppStateButton = this.menu.getByRole('button', { name: 'Reset App State' });
    this.cartLink = this.root.getByRole('button', { name: /^Cart,/ });
    this.cartBadge = this.root.getByTestId('shopping-cart-badge');
  }

  async openMenu(): Promise<void> {
    await this.openMenuButton.click();
    await this.menu.waitFor({ state: 'visible' });
  }

  async logout(): Promise<void> {
    await this.openMenu();
    await this.logoutButton.click();
  }

  async openCart(): Promise<void> {
    await this.cartLink.click();
    await this.page.waitForURL(/\/cart\.html/);
  }
}
