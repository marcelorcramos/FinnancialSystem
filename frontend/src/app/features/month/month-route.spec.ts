import { currentMonthPath, monthTitle, shiftMonth } from './month-route';

describe('month routes', () => {
  it('builds the current month path', () => {
    expect(currentMonthPath(new Date(2026, 9, 27))).toBe('/month/2026/10');
  });

  it('moves between months across years', () => {
    expect(shiftMonth(2026, 1, -1)).toEqual({ year: 2025, month: 12 });
    expect(shiftMonth(2026, 12, 1)).toEqual({ year: 2027, month: 1 });
    expect(shiftMonth(2026, 10, 0)).toEqual({ year: 2026, month: 10 });
  });

  it('names a month', () => {
    expect(monthTitle(2026, 10)).toBe('October 2026');
  });
});
