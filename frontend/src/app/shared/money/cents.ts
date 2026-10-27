/**
 * Money typed or adjusted in the UI is handled as integer cents, never as a
 * float: "220.5" -> 22050, 22050 -> "220.50". The API receives the string.
 */
const AMOUNT = /^\d{1,12}([.,]\d{0,2})?$/;

/** Cents of a typed amount ("220", "220.5", "220,50"), or null when it is not one. */
export function toCents(text: string): number | null {
  const value = text.trim();
  if (!AMOUNT.test(value)) return null;
  const [units, fraction = ''] = value.replace(',', '.').split('.');
  return Number(units) * 100 + Number(fraction.padEnd(2, '0'));
}

/** API decimal string for an amount in cents, e.g. 22050 -> "220.50". */
export function fromCents(cents: number): string {
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  return `${sign}${Math.trunc(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

/** Cents of an API decimal string that may be negative ("-12.50" -> -1250). */
export function signedCents(text: string): number | null {
  const value = text.trim();
  const negative = value.startsWith('-');
  const cents = toCents(negative ? value.slice(1) : value);
  return cents === null ? null : negative ? -cents : cents;
}
