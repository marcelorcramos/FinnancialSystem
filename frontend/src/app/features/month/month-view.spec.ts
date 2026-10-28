import { EntryListItem, LabelSummary, MonthSummary } from '../../core/api/types';
import { buildMonthView } from './month-view';

function label(
  name: string,
  kind: LabelSummary['kind'],
  parts: Partial<LabelSummary>,
): LabelSummary {
  return {
    label_id: name.toLowerCase(),
    name,
    kind,
    color: '#FFB74D',
    icon: 'restaurant',
    archived: false,
    allocation: '0.00',
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total: '0.00',
    ...parts,
  };
}

const SUMMARY: MonthSummary = {
  month_id: 'm10',
  year: 2026,
  month: 10,
  closed_at: null,
  income_total: '1050.00',
  distributed: '650.00',
  unallocated: '400.00',
  over_allocated: false,
  month_total: '650.00',
  by_kind: { expense: '212.00', saving: '288.00', investment: '150.00' },
  labels: [
    label('Food', 'expense', { allocation: '200.00', transfer_in: '12.00', total: '212.00' }),
    label('Housing', 'expense', {}),
    label('Savings', 'saving', { allocation: '300.00', transfer_out: '12.00', total: '288.00' }),
    label('Investments', 'investment', {
      allocation: '100.00',
      addition: '50.00',
      total: '150.00',
    }),
  ],
};

function entry(id: string, parts: Partial<EntryListItem>): EntryListItem {
  return {
    id,
    month_id: 'm10',
    label_id: 'food',
    amount: '0.00',
    movement_type: 'allocation',
    transfer_id: null,
    income_id: null,
    occurred_on: '2026-10-01',
    note: null,
    created_at: '2026-10-01T10:00:00Z',
    origin: 'initial_distribution',
    ...parts,
  };
}

const ENTRIES: EntryListItem[] = [
  entry('a1', { amount: '200.00' }),
  entry('a2', { label_id: 'savings', amount: '300.00', created_at: '2026-10-01T10:00:01Z' }),
  entry('x1', {
    label_id: 'investments',
    amount: '50.00',
    occurred_on: '2026-10-15',
    origin: 'external_income',
    movement_type: 'addition',
    source: 'Freelance',
  }),
  entry('t-out', {
    label_id: 'savings',
    amount: '12.00',
    occurred_on: '2026-10-20',
    origin: 'transfer_out',
    movement_type: 'transfer_out',
    counterpart_label_id: 'food',
  }),
  entry('t-in', {
    amount: '12.00',
    occurred_on: '2026-10-20',
    origin: 'transfer_in',
    movement_type: 'transfer_in',
    counterpart_label_id: 'savings',
  }),
];

describe('buildMonthView', () => {
  const view = buildMonthView(SUMMARY, ENTRIES);

  it('formats the month totals', () => {
    expect([view.income, view.spent, view.saved, view.invested, view.unallocated]).toEqual([
      '€1,050.00',
      '€212.00',
      '€288.00',
      '€150.00',
      '€400.00',
    ]);
    expect(view.distributedShare).toBe('61.9%');
    expect(view.overAllocated).toBe(false);
  });

  it('builds one donut segment per kind', () => {
    expect(view.segments.map((s) => [s.key, s.value, s.display, s.color])).toEqual([
      ['expense', 212, '€212.00', 'var(--kind-expense)'],
      ['saving', 288, '€288.00', 'var(--kind-saving)'],
      ['investment', 150, '€150.00', 'var(--kind-investment)'],
    ]);
  });

  it('builds one donut segment per label with money, in its own colour', () => {
    expect(view.labelSegments.map((s) => [s.label, s.value, s.display, s.color])).toEqual([
      ['Savings', 288, '€288.00', '#FFB74D'],
      ['Food', 212, '€212.00', '#FFB74D'],
      ['Investments', 150, '€150.00', '#FFB74D'],
    ]);
  });

  it('lists labels with money, largest first, with their base + adjustments', () => {
    expect(view.labels.map((l) => [l.name, l.total, l.share])).toEqual([
      ['Savings', '€288.00', '44.3%'],
      ['Food', '€212.00', '32.6%'],
      ['Investments', '€150.00', '23.1%'],
    ]);
    expect(view.labels.map((l) => l.detail)).toEqual([
      'Base €300.00 · −€12.00 moved out',
      'Base €200.00 · +€12.00 moved in',
      'Base €100.00 · +€50.00 extra income',
    ]);
  });

  it('shows recent entries newest first, each transfer once', () => {
    expect(view.recent.map((e) => [e.date, e.title, e.origin, e.amount])).toEqual([
      ['20 Oct', 'Savings → Food', 'Transfer', '€12.00'],
      ['15 Oct', 'Investments', 'Extra income · Freelance', '+€50.00'],
      ['1 Oct', 'Savings', 'Initial distribution', '€300.00'],
      ['1 Oct', 'Food', 'Initial distribution', '€200.00'],
    ]);
  });

  it('does not repeat the default source of extra income', () => {
    const entries = ENTRIES.map((e) =>
      e.source === 'Freelance' ? { ...e, source: 'Extra income' } : e,
    );
    expect(buildMonthView(SUMMARY, entries).recent[1]!.origin).toBe('Extra income');
  });

  it('limits the recent entries', () => {
    expect(buildMonthView(SUMMARY, ENTRIES, 2).recent.length).toBe(2);
  });
});
