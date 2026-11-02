/**
 * Helpers for prices shown as text, such as "$29.99" or "Item total: $45.98".
 * Money is handled in cents (integers) to avoid floating point drift.
 */
const AMOUNT = /-?\$\s?(\d[\d,]*)(?:\.(\d{1,2}))?/;

/** Returns the first dollar amount in the text as a number, for example 29.99. */
export function parseMoney(text: string): number {
  const match = AMOUNT.exec(text);
  if (!match) {
    throw new Error(`No dollar amount found in "${text}"`);
  }
  const whole = match[1]!.replace(/,/g, '');
  const cents = (match[2] ?? '0').padEnd(2, '0');
  const value = (Number(whole) * 100 + Number(cents)) / 100;
  return match[0].startsWith('-') ? -value : value;
}

/** Sums prices in cents and returns dollars rounded to two decimals. */
export function sumMoney(values: readonly number[]): number {
  const cents = values.reduce((total, value) => total + Math.round(value * 100), 0);
  return cents / 100;
}

/** Rounds to two decimals the way a checkout page displays tax and totals. */
export function roundMoney(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Formats 29.99 as "$29.99". */
export function formatMoney(value: number): string {
  return `$${value.toFixed(2)}`;
}
