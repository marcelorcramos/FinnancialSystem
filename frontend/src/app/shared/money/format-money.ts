/**
 * Monetary values travel as decimal strings (the backend serialises
 * NUMERIC(14,2) as strings), so they are never parsed into floats here.
 */
export type MoneyValue = string | number;

export const DEFAULT_CURRENCY = 'EUR';
// English UI: euros written as €1,234.50.
export const DEFAULT_MONEY_LOCALE = 'en-IE';

const DECIMAL_PATTERN = /^[-+]?\d+(\.\d+)?$/;
const formatters = new Map<string, Intl.NumberFormat>();

function formatter(locale: string, currency: string): Intl.NumberFormat {
  const key = `${locale}|${currency}`;
  let cached = formatters.get(key);
  if (!cached) {
    cached = new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    formatters.set(key, cached);
  }
  return cached;
}

export function isMoneyValue(value: unknown): value is MoneyValue {
  if (typeof value === 'number') {
    return Number.isFinite(value);
  }
  return typeof value === 'string' && DECIMAL_PATTERN.test(value.trim());
}

/** Formats a value as currency, e.g. "1234.5" -> "€1,234.50". */
export function formatMoney(
  value: MoneyValue,
  currency: string = DEFAULT_CURRENCY,
  locale: string = DEFAULT_MONEY_LOCALE,
): string {
  if (!isMoneyValue(value)) {
    return '—';
  }
  const input = typeof value === 'string' ? value.trim() : value;
  // Intl.NumberFormat formats decimal strings exactly (ES2023), without a
  // round trip through a float; the cast only satisfies the ES2022 lib types.
  return formatter(locale, currency).format(input as number);
}
