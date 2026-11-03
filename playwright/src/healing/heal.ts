import fs from 'node:fs';
import path from 'node:path';
import { test, type Locator, type Page } from '@playwright/test';

/**
 * Self-healing locators, heal-and-propose style.
 *
 * A healing locator takes an ordered list of candidates. The first candidate is
 * the one the test is written against. When it does not attach in time, the
 * next candidates are tried in order. When a fallback wins, the heal is
 * recorded as an event and shown as an annotation in the HTML report. The
 * report turns events into proposals for a person to review.
 *
 * What this module never does: it never rewrites a test, and it never hides a
 * heal. The unhealed run stays the release gate in CI. A heal is a signal that
 * the primary locator went stale, or that the page changed in a way a person
 * must look at.
 */
export interface LocatorCandidate {
  /** The locator as code, for example "getByTestId('add-to-cart-sauce-labs-backpack')". Printed in reports. */
  describe: string;
  build: (page: Page) => Locator;
}

export interface HealingOptions {
  /** Short name of the element, for example "add to cart (backpack)". */
  name: string;
  /** What the test wants to do with the element. Goes into the proposal. */
  intent: string;
  /** Ordered candidates. Index 0 is the primary locator. */
  candidates: LocatorCandidate[];
  /** Time each candidate gets to attach, in milliseconds. Default 1500. */
  timeout?: number;
}

export interface HealingEvent {
  timestamp: string;
  test: string;
  project: string;
  url: string;
  name: string;
  intent: string;
  primary: string;
  winnerIndex: number;
  winner: string;
  proposal: string;
}

export const HEALING_DIR = path.resolve(__dirname, '../../results/healing');
export const EVENTS_FILE = path.join(HEALING_DIR, 'events.jsonl');

/**
 * Resolves the first candidate that attaches to the page. Records a healing
 * event when the winner is not the primary. Throws when nothing attaches.
 */
export async function healingLocator(page: Page, options: HealingOptions): Promise<Locator> {
  const timeout = options.timeout ?? 1_500;
  if (options.candidates.length === 0) {
    throw new Error(`healingLocator "${options.name}": no candidates were given`);
  }

  const tried: string[] = [];
  for (let index = 0; index < options.candidates.length; index++) {
    const candidate = options.candidates[index]!;
    tried.push(candidate.describe);
    const locator = candidate.build(page);
    if (await isAttached(locator, timeout)) {
      if (index > 0) {
        recordHeal(page, options, index);
      }
      return locator;
    }
  }

  throw new Error(
    `healingLocator "${options.name}": none of ${tried.length} candidates attached within ${timeout} ms each.\n` +
      tried.map((text, i) => `  ${i === 0 ? 'primary' : 'fallback'} ${i}: ${text}`).join('\n'),
  );
}

/** Attach check on `.first()`, so a candidate that matches several elements is not rejected here. Strictness still applies when the test acts on the returned locator. */
async function isAttached(locator: Locator, timeout: number): Promise<boolean> {
  try {
    await locator.first().waitFor({ state: 'attached', timeout });
    return true;
  } catch {
    return false;
  }
}

function recordHeal(page: Page, options: HealingOptions, winnerIndex: number): void {
  const primary = options.candidates[0]!;
  const winner = options.candidates[winnerIndex]!;
  const info = currentTestInfo();
  const event: HealingEvent = {
    timestamp: new Date().toISOString(),
    test: info?.title ?? 'unknown test',
    project: info?.project.name ?? 'unknown project',
    url: page.url(),
    name: options.name,
    intent: options.intent,
    primary: primary.describe,
    winnerIndex,
    winner: winner.describe,
    proposal:
      `Replace ${primary.describe} with ${winner.describe} for "${options.name}" (${options.intent}). ` +
      'Check the page first: a heal can land on a similar element and pass the wrong assertion.',
  };

  fs.mkdirSync(HEALING_DIR, { recursive: true });
  // One JSON line per event. Appends are small and atomic, so parallel workers can share the file.
  fs.appendFileSync(EVENTS_FILE, JSON.stringify(event) + '\n');

  info?.annotations.push({
    type: 'healed',
    description: `${options.name}: ${primary.describe} did not attach, used fallback ${winnerIndex} ${winner.describe}`,
  });
  console.warn(`[healing] ${event.test}: ${event.name} healed with fallback ${winnerIndex} (${winner.describe})`);
}

function currentTestInfo() {
  try {
    return test.info();
  } catch {
    return undefined;
  }
}

/** Reads every recorded event. Returns an empty list when no heal happened. */
export function readHealingEvents(): HealingEvent[] {
  if (!fs.existsSync(EVENTS_FILE)) return [];
  return fs
    .readFileSync(EVENTS_FILE, 'utf8')
    .split('\n')
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as HealingEvent);
}
