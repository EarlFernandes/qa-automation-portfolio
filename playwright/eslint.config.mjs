import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import playwright from 'eslint-plugin-playwright';

export default tseslint.config(
  { ignores: ['node_modules/', 'test-results/', 'playwright-report/', 'results/'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    ...playwright.configs['flat/recommended'],
    files: ['tests/**/*.ts'],
    rules: {
      ...playwright.configs['flat/recommended'].rules,
      // Page objects own the raw locators, so tests may call their methods inside expect.
      'playwright/expect-expect': ['error', { assertFunctionNames: ['expect', 'expectSortedAscending'] }],
    },
  },
);
