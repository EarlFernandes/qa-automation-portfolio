import { test, expect } from '../../src/fixtures/test';
import { formatMoney, parseMoney, roundMoney, sumMoney } from '../../src/utils/money';

// Runs in the `unit` project: no browser, no sign-in.
test.describe('money helpers', () => {
  test('parseMoney reads a plain price', () => {
    expect(parseMoney('$29.99')).toBe(29.99);
  });

  test('parseMoney reads an amount inside a label', () => {
    expect(parseMoney('Item total: $45.98')).toBe(45.98);
  });

  test('parseMoney handles thousands separators and one decimal', () => {
    expect(parseMoney('$1,234.5')).toBe(1234.5);
  });

  test('parseMoney throws when there is no amount', () => {
    expect(() => parseMoney('free')).toThrow('No dollar amount found');
  });

  test('sumMoney avoids floating point drift', () => {
    expect(sumMoney([0.1, 0.2])).toBe(0.3);
    expect(sumMoney([29.99, 9.99, 15.99])).toBe(55.97);
  });

  test('roundMoney rounds to cents', () => {
    expect(roundMoney(4.4776)).toBe(4.48);
    expect(roundMoney(2.3992)).toBe(2.4);
  });

  test('formatMoney prints two decimals', () => {
    expect(formatMoney(2.4)).toBe('$2.40');
  });
});
