import fs from 'node:fs';
import path from 'node:path';
import { EVENTS_FILE, HEALING_DIR, readHealingEvents, type HealingEvent } from './heal';

export const REPORT_FILE = path.resolve(HEALING_DIR, '../healing-report.md');

/**
 * Global teardown. Turns the healing events of this run into a Markdown report
 * with one proposal per heal. In GitHub Actions the same Markdown is appended
 * to the job summary, so a reviewer sees the proposals without opening files.
 */
export default async function healingReport(): Promise<void> {
  const events = readHealingEvents();
  const markdown = renderReport(events);

  fs.mkdirSync(path.dirname(REPORT_FILE), { recursive: true });
  fs.writeFileSync(REPORT_FILE, markdown);

  const summaryFile = process.env.GITHUB_STEP_SUMMARY;
  if (summaryFile) {
    fs.appendFileSync(summaryFile, markdown + '\n');
  }

  console.log(
    events.length === 0
      ? '[healing] 0 locators healed'
      : `[healing] ${events.length} locator${events.length === 1 ? '' : 's'} healed, review the proposals in ${REPORT_FILE} before changing tests`,
  );
}

/** Deletes the events of a previous run. Called from global setup. */
export function resetHealingEvents(): void {
  if (fs.existsSync(EVENTS_FILE)) fs.rmSync(EVENTS_FILE);
}

export function renderReport(events: HealingEvent[]): string {
  const lines: string[] = ['## Self-healing locators', ''];
  if (events.length === 0) {
    lines.push('0 locators healed in this run.', '');
    return lines.join('\n');
  }
  lines.push(
    `${events.length} locator${events.length === 1 ? '' : 's'} healed. Each row is a proposal. Review the page before changing a test: a heal can land on a similar element.`,
    '',
    '| Test | Project | Page | Primary | Healed with | Proposal |',
    '| --- | --- | --- | --- | --- | --- |',
  );
  for (const event of events) {
    lines.push(
      `| ${cell(event.test)} | ${cell(event.project)} | ${cell(event.url)} | ${code(event.primary)} | ${code(event.winner)} | ${cell(event.proposal)} |`,
    );
  }
  lines.push('');
  return lines.join('\n');
}

function cell(text: string): string {
  return text.replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function code(text: string): string {
  return '`' + text.replace(/`/g, "'").replace(/\|/g, '\\|') + '`';
}
