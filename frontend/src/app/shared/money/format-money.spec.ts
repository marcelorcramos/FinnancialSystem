import { formatMoney, isMoneyValue } from './format-money';

// Intl uses (narrow) no-break spaces; normalise them to compare.
const normalise = (s: string) => s.replace(/[\u00a0\u202f]/g, ' ');

describe('formatMoney', () => {
  it('formats EUR in pt-PT by default', () => {
    expect(normalise(formatMoney('212.00'))).toBe('212,00 €');
    expect(normalise(formatMoney('12345.6'))).toBe('12 345,60 €');
  });

  it('always shows two decimals', () => {
    expect(normalise(formatMoney('50'))).toBe('50,00 €');
    expect(normalise(formatMoney(0))).toBe('0,00 €');
  });

  it('formats decimal strings exactly, without float rounding', () => {
    // 0.1 + 0.2 style errors must not leak into the UI.
    expect(normalise(formatMoney('999999999999.99'))).toBe('999 999 999 999,99 €');
    expect(normalise(formatMoney('0.30'))).toBe('0,30 €');
  });

  it('formats negative values (e.g. a saving label used this month)', () => {
    expect(normalise(formatMoney('-12.5'))).toBe('-12,50 €');
  });

  it('supports another locale', () => {
    expect(formatMoney('1234.5', 'EUR', 'en')).toBe('€1,234.50');
  });

  it('returns a dash for invalid input', () => {
    expect(formatMoney('abc')).toBe('—');
    expect(formatMoney(Number.NaN)).toBe('—');
  });
});

describe('isMoneyValue', () => {
  it('accepts decimal strings and finite numbers', () => {
    expect(isMoneyValue('12.34')).toBe(true);
    expect(isMoneyValue(' 7 ')).toBe(true);
    expect(isMoneyValue(5)).toBe(true);
  });

  it('rejects anything else', () => {
    expect(isMoneyValue('1,5')).toBe(false);
    expect(isMoneyValue('')).toBe(false);
    expect(isMoneyValue(Infinity)).toBe(false);
    expect(isMoneyValue(null)).toBe(false);
  });
});
