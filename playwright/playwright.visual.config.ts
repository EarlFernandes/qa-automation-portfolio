import { defineConfig, devices } from '@playwright/test';
import baseConfig, { STORAGE_STATE } from './playwright.config';

/**
 * Visual regression runs on demand with `npm run test:visual`.
 *
 * It has its own config because screenshot baselines are tied to one
 * platform and browser build. The committed baselines come from Linux and
 * the Chromium that ships with Playwright 1.63, the same pair that CI would
 * use. A run on macOS or Windows renders fonts differently and would fail
 * against them, so the visual project is not part of the default run.
 */
export default defineConfig({
  ...baseConfig,
  globalSetup: undefined,
  globalTeardown: undefined,
  snapshotPathTemplate: '{testDir}/visual/__screenshots__/{testFileName}/{arg}{ext}',
  expect: {
    ...baseConfig.expect,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
      animations: 'disabled',
      caret: 'hide',
    },
  },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-visual' }]],
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'visual',
      testMatch: /tests\/visual\/.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], storageState: STORAGE_STATE },
      dependencies: ['setup'],
    },
  ],
});
