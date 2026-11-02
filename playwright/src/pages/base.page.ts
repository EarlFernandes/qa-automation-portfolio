import type { Locator, Page } from '@playwright/test';
import { HeaderComponent } from '../components/header.component';

/**
 * Shared behaviour for every page object: navigation to the page's path and
 * access to the header. Each page declares its own `path` and `title`.
 */
export abstract class BasePage {
  readonly header: HeaderComponent;
  /** The page heading shown under the header, for example "Products". */
  readonly title: Locator;

  protected constructor(
    protected readonly page: Page,
    readonly path: string,
  ) {
    this.header = new HeaderComponent(page);
    this.title = page.getByTestId('title');
  }

  async goto(): Promise<void> {
    await this.page.goto(this.path);
  }

  /** Resolves when the browser URL matches this page's path. */
  async waitForPage(): Promise<void> {
    await this.page.waitForURL(new RegExp(`${escapeRegExp(this.path)}(\\?.*)?$`));
  }
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
