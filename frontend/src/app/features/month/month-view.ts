import { EntryListItem, LabelSummary, MonthSummary } from '../../core/api/types';
import { DonutSegment } from '../../shared/charts/donut';
import { formatMoney } from '../../shared/money/format-money';
import { Kind } from '../../shared/money/kind';

/** Money comes as decimal strings; numbers are used only to size, sort and compute shares. */
const amount = (value: string): number => Number(value);
const isZero = (value: string): boolean => amount(value) === 0;

export interface LabelRow {
  id: string;
  name: string;
  kind: Kind;
  color: string;
  icon: string;
  total: string;
  share: string;
  /** "Base €200.00 · +€12.00 from transfers", the base + adjustments story. */
  detail: string;
}

export interface RecentEntry {
  id: string;
  date: string;
  title: string;
  origin: string;
  amount: string;
  /** Money that came from outside the app, shown with a plus sign. */
  incoming: boolean;
}

export interface MonthView {
  income: string;
  spent: string;
  saved: string;
  invested: string;
  distributed: string;
  unallocated: string;
  overAllocated: boolean;
  distributedShare: string;
  /** Donut "Overview": one slice per kind (spent, saved, invested). */
  segments: DonutSegment[];
  /** Donut "Detailed": one slice per label, in the label's own colour. */
  labelSegments: DonutSegment[];
  labels: LabelRow[];
  recent: RecentEntry[];
}

const KIND_SEGMENTS: { kind: Kind; label: string }[] = [
  { kind: 'expense', label: 'Spent' },
  { kind: 'saving', label: 'Saved' },
  { kind: 'investment', label: 'Invested' },
];

function percent(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(1)}%` : '0.0%';
}

function labelDetail(label: LabelSummary): string {
  const parts = [`Base ${formatMoney(label.allocation)}`];
  if (!isZero(label.addition)) parts.push(`+${formatMoney(label.addition)} extra income`);
  if (!isZero(label.transfer_in)) parts.push(`+${formatMoney(label.transfer_in)} moved in`);
  if (!isZero(label.transfer_out)) parts.push(`−${formatMoney(label.transfer_out)} moved out`);
  return parts.join(' · ');
}

function shortDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year!, month! - 1, day!).toLocaleDateString('en-GB', {
    month: 'short',
    day: 'numeric',
  });
}

function recentEntries(entries: EntryListItem[], names: Map<string, string>, limit: number) {
  const name = (id: string | null | undefined) => (id ? (names.get(id) ?? 'Unknown label') : '');
  return (
    entries
      // A transfer is shown once, from its outgoing leg.
      .filter((entry) => entry.origin !== 'transfer_in')
      .sort(
        (a, b) =>
          b.occurred_on.localeCompare(a.occurred_on) || b.created_at.localeCompare(a.created_at),
      )
      .slice(0, limit)
      .map((entry): RecentEntry => {
        const date = shortDate(entry.occurred_on);
        const money = formatMoney(entry.amount);
        switch (entry.origin) {
          case 'transfer_out':
            return {
              id: entry.id,
              date,
              title: `${name(entry.label_id)} → ${name(entry.counterpart_label_id)}`,
              origin: 'Transfer',
              amount: money,
              incoming: false,
            };
          case 'external_income':
            return {
              id: entry.id,
              date,
              title: name(entry.label_id),
              origin: entry.source ? `Extra income · ${entry.source}` : 'Extra income',
              amount: `+${money}`,
              incoming: true,
            };
          default:
            return {
              id: entry.id,
              date,
              title: name(entry.label_id),
              origin: 'Initial distribution',
              amount: money,
              incoming: false,
            };
        }
      })
  );
}

/** Everything the month screen shows, derived from the API summary and entries. */
export function buildMonthView(
  summary: MonthSummary,
  entries: EntryListItem[],
  recentLimit = 6,
): MonthView {
  const distributed = amount(summary.distributed);
  const byKind = summary.by_kind as Record<Kind, string>;
  const names = new Map(summary.labels.map((label) => [label.label_id, label.name]));
  const positiveTotal = summary.labels.reduce((sum, l) => sum + Math.max(amount(l.total), 0), 0);
  const withMoney = summary.labels
    .filter((label) => !isZero(label.total))
    .sort((a, b) => amount(b.total) - amount(a.total) || a.name.localeCompare(b.name));

  return {
    income: formatMoney(summary.income_total),
    spent: formatMoney(byKind.expense ?? '0'),
    saved: formatMoney(byKind.saving ?? '0'),
    invested: formatMoney(byKind.investment ?? '0'),
    distributed: formatMoney(summary.distributed),
    unallocated: formatMoney(summary.unallocated),
    overAllocated: summary.over_allocated,
    distributedShare: percent(distributed, amount(summary.income_total)),
    segments: KIND_SEGMENTS.map(({ kind, label }) => ({
      key: kind,
      label,
      value: amount(byKind[kind] ?? '0'),
      color: `var(--kind-${kind})`,
      display: formatMoney(byKind[kind] ?? '0'),
    })),
    labelSegments: withMoney.map((label) => ({
      key: label.label_id,
      label: label.name,
      value: amount(label.total),
      color: label.color,
      display: formatMoney(label.total),
    })),
    labels: withMoney.map((label) => ({
      id: label.label_id,
      name: label.name,
      kind: label.kind,
      color: label.color,
      icon: label.icon,
      total: formatMoney(label.total),
      share: percent(Math.max(amount(label.total), 0), positiveTotal),
      detail: labelDetail(label),
    })),
    recent: recentEntries(entries, names, recentLimit),
  };
}
