/** Axis texts shared by the charts. */

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-05" -> "May"; the year is added when the series crosses one ("Jan 27"). */
export function monthLabel(key: string, withYear: boolean): string {
  const [year, month] = key.split('-');
  const name = MONTHS[Number(month) - 1]!;
  return withYear ? `${name} ${year!.slice(2)}` : name;
}

/** Axis text in whole euros: 1234 -> "€1,234". */
export function wholeEuros(value: number): string {
  const euros = Math.round(Math.abs(value));
  return `${value < 0 ? '−' : ''}€${euros.toLocaleString('en-IE')}`;
}
