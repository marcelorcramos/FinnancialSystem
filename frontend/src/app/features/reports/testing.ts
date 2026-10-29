import { ReportEntry, ReportLabel, ReportSummary } from '../../core/api/types';

/** Report fixtures shared by the specs. */

export function reportLabel(name: string, extra: Partial<ReportLabel> = {}): ReportLabel {
  return {
    label_id: name.toLowerCase(),
    name,
    kind: 'expense',
    color: '#FFB74D',
    icon: 'restaurant',
    archived: false,
    allocation: '0.00',
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total: '0.00',
    share: '0.00',
    ...extra,
  };
}

export const SUMMARY: ReportSummary = {
  period: 'last_6_months',
  start_month: '2026-05',
  end_month: '2026-10',
  reference_date: '2026-10-29',
  total: '500.00',
  by_kind: { expense: '212.00', saving: '288.00', investment: '0.00' },
  kind_shares: { expense: '42.40', saving: '57.60', investment: '0.00' },
  labels: [
    reportLabel('Savings', {
      kind: 'saving',
      allocation: '300.00',
      transfer_out: '12.00',
      total: '288.00',
      share: '57.60',
    }),
    reportLabel('Food', {
      allocation: '150.00',
      addition: '50.00',
      transfer_in: '12.00',
      total: '212.00',
      share: '42.40',
    }),
    reportLabel('Gym'),
  ],
};

export function reportEntry(extra: Partial<ReportEntry>): ReportEntry {
  return {
    id: 'e1',
    month_id: 'm10',
    month: '2026-10',
    label_id: 'food',
    amount: '150.00',
    movement_type: 'allocation',
    transfer_id: null,
    income_id: null,
    occurred_on: '2026-10-01',
    note: null,
    created_at: '2026-10-01T09:00:00Z',
    origin: 'initial_distribution',
    source: null,
    counterpart_label_id: null,
    ...extra,
  };
}
