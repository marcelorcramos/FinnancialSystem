/** Path of a month screen, e.g. /month/2026/10. */
export function monthPath(year: number, month: number): string {
  return `/month/${year}/${month}`;
}

export function currentMonthPath(today = new Date()): string {
  return monthPath(today.getFullYear(), today.getMonth() + 1);
}

/** The month before or after, crossing years. */
export function shiftMonth(
  year: number,
  month: number,
  delta: number,
): { year: number; month: number } {
  const index = year * 12 + (month - 1) + delta;
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

export function monthTitle(year: number, month: number): string {
  return new Date(year, month - 1, 1).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
  });
}
