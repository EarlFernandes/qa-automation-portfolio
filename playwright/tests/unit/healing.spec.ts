import { test, expect } from '../../src/fixtures/test';
import { renderReport } from '../../src/healing/report';
import { buildProposalPrompt, parseProposal, proposeLocatorWithModel } from '../../src/healing/llm-proposer';
import type { HealingEvent } from '../../src/healing/heal';

// Runs in the `unit` project: no browser, no sign-in.
test.describe('healing report', () => {
  test('renders a zero line when nothing healed', () => {
    expect(renderReport([])).toContain('0 locators healed');
  });

  test('renders one table row per event with code cells', () => {
    const event: HealingEvent = {
      timestamp: '2026-01-01T00:00:00.000Z',
      test: 'adds a backpack',
      project: 'chromium',
      url: 'https://www.saucedemo.com/inventory.html',
      name: 'add to cart (backpack)',
      intent: 'add the backpack',
      primary: "getByTestId('legacy')",
      winnerIndex: 1,
      winner: "getByRole('button', { name: 'Add to cart' })",
      proposal: "Replace getByTestId('legacy') with getByRole('button', { name: 'Add to cart' })",
    };
    const markdown = renderReport([event]);
    expect(markdown).toContain('1 locator healed');
    expect(markdown).toContain("| adds a backpack | chromium | https://www.saucedemo.com/inventory.html | `getByTestId('legacy')` |");
    expect(markdown).toContain('| Test | Project | Page | Primary | Healed with | Proposal |');
  });
});

test.describe('LLM proposer (reference only)', () => {
  test('prompt carries the intent and the aria snapshot and asks for a role-based locator', () => {
    const prompt = buildProposalPrompt('- button "Add to cart"', 'add the backpack');
    expect(prompt).toContain('The test wants to: add the backpack.');
    expect(prompt).toContain('- button "Add to cart"');
    expect(prompt).toContain('Prefer getByRole');
    expect(prompt).toContain('Never propose XPath');
  });

  test('parses a plain JSON proposal', () => {
    expect(parseProposal('{"locator":"getByRole(\'button\', { name: \'Add to cart\' })","reason":"Only button with that name"}')).toEqual({
      locator: "getByRole('button', { name: 'Add to cart' })",
      reason: 'Only button with that name',
    });
  });

  test('parses a proposal wrapped in a code fence', () => {
    const text = '```json\n{"locator":"getByLabel(\'Username\')","reason":"Labelled input"}\n```';
    expect(parseProposal(text).locator).toBe("getByLabel('Username')");
  });

  test('rejects a proposal without the required fields', () => {
    expect(() => parseProposal('{"locator": 42}')).toThrow('Proposal must contain string fields');
  });

  test('is off by default and refuses to call a model', async () => {
    await expect(proposeLocatorWithModel('- button "Login"', 'sign in')).rejects.toThrow('The LLM locator proposer is off');
  });
});
