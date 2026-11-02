import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for the Swag Labs demo shop (https://www.saucedemo.com).
 *
 * Design choices:
 * - `testIdAttribute` is `data-test` because that is the attribute the site exposes.
 * - A `setup` project logs in once and saves the browser state. The browser projects
 *   depend on it and start every test already signed in. Tests that need a signed-out
 *   browser override `storageState` locally.
 * - Traces, screenshots and videos are kept only when a test fails or retries, so the
 *   report stays small and still has what you need to debug.
 */
const isCI = !!process.env.CI;
/** Written by tests/auth.setup.ts and read by the browser projects. */
export const STORAGE_STATE = path.join(__dirname, '.auth/standard_user.json');

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 2 : undefined,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  outputDir: 'test-results',

  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'results/junit.xml' }],
    ...(isCI ? [['github'] as const] : []),
  ],

  use: {
    baseURL: process.env.BASE_URL ?? 'https://www.saucedemo.com',
    testIdAttribute: 'data-test',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    // Pure TypeScript checks. No browser, no sign-in.
    {
      name: 'unit',
      testMatch: /tests\/unit\/.*\.spec\.ts/,
    },
    // Signs in once and writes the storage state file used by the browser projects.
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      testIgnore: /tests\/unit\//,
      use: { ...devices['Desktop Chrome'], storageState: STORAGE_STATE },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      testIgnore: /tests\/unit\//,
      use: { ...devices['Pixel 7'], storageState: STORAGE_STATE },
      dependencies: ['setup'],
    },
    // To add more engines, install them with `npx playwright install firefox webkit`
    // and add projects that spread devices['Desktop Firefox'] and devices['Desktop Safari'].
  ],
});
