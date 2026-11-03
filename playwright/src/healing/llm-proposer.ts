/**
 * Reference extension point: ask a language model for a locator proposal.
 *
 * This is off by default and never runs in the suite or in CI. It exists to
 * show where a model would fit: after the rule-based fallbacks in heal.ts have
 * failed, a model can read the page's aria snapshot and propose a role-based
 * locator. The proposal is text for a person to review. It is never applied
 * to a test by code.
 *
 * To try it by hand:
 *   HEAL_LLM=1 ANTHROPIC_API_KEY=... node -e "..."  (see README)
 */
export interface LocatorProposal {
  locator: string;
  reason: string;
}

export const PROPOSER_MODEL = process.env.HEAL_LLM_MODEL ?? 'claude-haiku-4-5';

/** Builds the prompt. Pure function, covered by a unit test. */
export function buildProposalPrompt(ariaSnapshot: string, intent: string): string {
  return [
    'You help maintain Playwright tests. A locator stopped matching.',
    `The test wants to: ${intent}.`,
    'Below is the aria snapshot of the page. Propose ONE Playwright locator that finds the element for this intent.',
    'Prefer getByRole with an accessible name. Use getByLabel, getByPlaceholder or getByText only when no role fits.',
    'Never propose XPath or CSS tied to styling classes.',
    'Answer as JSON with two keys: "locator" (the code) and "reason" (one sentence).',
    '',
    'Aria snapshot:',
    ariaSnapshot,
  ].join('\n');
}

export function proposerEnabled(): boolean {
  return process.env.HEAL_LLM === '1' && Boolean(process.env.ANTHROPIC_API_KEY);
}

/**
 * Sends the prompt to the model and returns its proposal. Throws when the
 * proposer is not enabled, so an accidental call in a test fails loudly.
 */
export async function proposeLocatorWithModel(ariaSnapshot: string, intent: string): Promise<LocatorProposal> {
  if (!proposerEnabled()) {
    throw new Error(
      'The LLM locator proposer is off. Set HEAL_LLM=1 and ANTHROPIC_API_KEY to use it by hand. It never runs in CI.',
    );
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY as string,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: PROPOSER_MODEL,
      max_tokens: 300,
      messages: [{ role: 'user', content: buildProposalPrompt(ariaSnapshot, intent) }],
    }),
  });
  if (!response.ok) {
    throw new Error(`Proposer request failed: HTTP ${response.status}`);
  }

  const body = (await response.json()) as { content?: Array<{ type: string; text?: string }> };
  const text = body.content?.find((part) => part.type === 'text')?.text ?? '';
  return parseProposal(text);
}

/** Accepts plain JSON or JSON inside a code fence. Pure function, covered by a unit test. */
export function parseProposal(text: string): LocatorProposal {
  const stripped = text.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '').trim();
  const parsed = JSON.parse(stripped) as Partial<LocatorProposal>;
  if (typeof parsed.locator !== 'string' || typeof parsed.reason !== 'string') {
    throw new Error('Proposal must contain string fields "locator" and "reason"');
  }
  return { locator: parsed.locator, reason: parsed.reason };
}
