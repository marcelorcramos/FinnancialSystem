import { ReportSeries } from '../../core/api/types';
import { buildReportView, buildTrend, entryRows, windowText } from './report-view';
import { reportEntry, SUMMARY } from './testing';

describe('windowText', () => {
  it('names the window, or all time', () => {
    expect(windowText('2026-05', '2026-10')).toBe('May 2026 – Oct 2026');
    expect(windowText('2026-10', '2026-10')).toBe('Oct 2026');
    expect(windowText(null, null)).toBe('Since the first month');
  });
});

describe('buildReportView', () => {
  const view = buildReportView(SUMMARY);

  it('shows the totals and one slice per kind or label', () => {
    expect([view.total, view.spent, view.saved, view.invested]).toEqual([
      '€500.00',
      '€212.00',
      '€288.00',
      '€0.00',
    ]);
    expect(view.window).toBe('May 2026 – Oct 2026');
    expect(view.kindSegments.map((s) => [s.label, s.value])).toEqual([
      ['Spent', 21200],
      ['Saved', 28800],
      ['Invested', 0],
    ]);
    expect(view.labelSegments.map((s) => s.label)).toEqual(['Savings', 'Food']);
  });

  it('builds each bar from what came in, with what moved out at its end', () => {
    const [savings, food] = view.bars;
    expect(savings!.width).toBe(100);
    expect(savings!.parts).toEqual([{ part: 'base', width: 100 }]);
    expect(savings!.movedOut).toBe(4);
    expect(savings!.movedOutText).toBe('−€12.00');
    expect(food!.width).toBeCloseTo(70.67, 2);
    expect(food!.parts.map((p) => p.part)).toEqual(['base', 'extra', 'moved-in']);
    expect(food!.detail).toBe('Base €150.00 · +€50.00 extra income · +€12.00 moved in');
    expect(food!.share).toBe('42.4%');
  });

  it('counts the selected labels without money apart', () => {
    expect(view.bars.map((b) => b.name)).toEqual(['Savings', 'Food']);
    expect(view.empty).toBe(1);
  });
});

describe('buildTrend', () => {
  const series = {
    months: ['2026-09', '2026-10'],
    totals: [
      { month: '2026-09', total: '100.00' },
      { month: '2026-10', total: '250.50' },
    ],
  } as ReportSeries;

  it('reads the combined total of every month', () => {
    const trend = buildTrend(series)!;
    expect(trend.points.map((p) => [p.label, p.display])).toEqual([
      ['Sep', '€100.00'],
      ['Oct', '€250.50'],
    ]);
    expect([trend.average, trend.highest, trend.highestMonth]).toEqual([
      '€175.25',
      '€250.50',
      'Oct 26',
    ]);
    expect(trend.aria).toBe('Selected labels per month: Sep €100.00, Oct €250.50');
  });

  it('is skipped for a single month', () => {
    expect(buildTrend({ ...series, months: ['2026-10'], totals: [series.totals[1]!] })).toBeNull();
  });
});

describe('entryRows', () => {
  const labels = new Map([
    ['food', { name: 'Food', color: '#FFB74D' }],
    ['savings', { name: 'Savings', color: '#5FD39A' }],
  ]);

  it('tells where the money of each entry came from', () => {
    const rows = entryRows(
      [
        reportEntry({
          id: 'a',
          origin: 'transfer_in',
          amount: '12.00',
          counterpart_label_id: 'savings',
        }),
        reportEntry({
          id: 'b',
          label_id: 'savings',
          origin: 'transfer_out',
          amount: '12.00',
          counterpart_label_id: 'food',
        }),
        reportEntry({ id: 'c', origin: 'external_income', amount: '50.00', source: 'Bonus' }),
        reportEntry({ id: 'd', label_id: 'gone' }),
      ],
      labels,
    );
    expect(rows.map((r) => [r.label, r.origin, r.amount])).toEqual([
      ['Food', 'Moved from Savings', '+€12.00'],
      ['Savings', 'Moved to Food', '−€12.00'],
      ['Food', 'Extra income · Bonus', '+€50.00'],
      ['Deleted label', 'Initial distribution', '€150.00'],
    ]);
    expect(rows[1]!.outgoing).toBe(true);
    expect(rows[0]!.date).toBe('1 Oct 2026');
  });
});
