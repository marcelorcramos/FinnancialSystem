import {
  ReportEntry,
  ReportLabel,
  ReportPeriod,
  ReportSeries,
  ReportSummary,
} from '../../core/api/types';
import { DonutSegment } from '../../shared/charts/donut';
import { LinePoint } from '../../shared/charts/line-chart';
import { monthLabel } from '../../shared/charts/month-label';
import { fromCents, signedCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { Kind } from '../../shared/money/kind';
import { labelDetail } from '../month/month-view';

export const REPORT_PERIODS: { value: ReportPeriod; text: string }[] = [
  { value: 'last_month', text: 'This month' },
  { value: 'last_6_months', text: 'Last 6 months' },
  { value: 'last_12_months', text: 'Last 12 months' },
  { value: 'all', text: 'All time' },
];

const cents = (value: string): number => signedCents(value) ?? 0;

/** A part of a label bar, as a percentage of the bar. */
export interface BarPart {
  part: 'base' | 'extra' | 'moved-in';
  width: number;
}

/** One label in the sorted bars: what came in, and what moved out of it. */
export interface LabelBar {
  id: string;
  name: string;
  kind: Kind;
  color: string;
  archived: boolean;
  total: string;
  share: string;
  detail: string;
  /** Width of the whole bar (money that came in), relative to the largest one. */
  width: number;
  parts: BarPart[];
  /** Share of the bar that moved out to other labels (drawn striped at its end). */
  movedOut: number;
  /** Text-alternative columns. */
  base: string;
  extra: string;
  movedIn: string;
  movedOutText: string;
}

export interface ReportView {
  window: string;
  total: string;
  spent: string;
  saved: string;
  invested: string;
  kindSegments: DonutSegment[];
  labelSegments: DonutSegment[];
  bars: LabelBar[];
  /** Selected labels with no money in the window (listed only as a count). */
  empty: number;
}

const KIND_SEGMENTS: { kind: Kind; label: string; pattern?: 'lines' | 'dots' }[] = [
  { kind: 'expense', label: 'Spent' },
  { kind: 'saving', label: 'Saved', pattern: 'lines' },
  { kind: 'investment', label: 'Invested', pattern: 'dots' },
];

function percentText(value: string): string {
  return `${Number(value).toFixed(1)}%`;
}

/** "May 2026 – Oct 2026", "Oct 2026" or "Since the first month". */
export function windowText(start: string | null | undefined, end: string | null | undefined) {
  if (!start || !end) return 'Since the first month';
  const text = (key: string) => {
    const [year] = key.split('-');
    return `${monthLabel(key, false)} ${year}`;
  };
  return start === end ? text(start) : `${text(start)} – ${text(end)}`;
}

function bar(label: ReportLabel, largest: number): LabelBar {
  const base = cents(label.allocation);
  const extra = cents(label.addition);
  const movedIn = cents(label.transfer_in);
  const movedOut = cents(label.transfer_out);
  const gross = base + extra + movedIn;
  const of = (part: number) => (gross > 0 ? (part / gross) * 100 : 0);
  return {
    id: label.label_id,
    name: label.name,
    kind: label.kind,
    color: label.color,
    archived: label.archived,
    total: formatMoney(label.total),
    share: percentText(label.share),
    detail: labelDetail(label),
    width: largest > 0 ? (gross / largest) * 100 : 0,
    parts: (
      [
        { part: 'base', width: of(base) },
        { part: 'extra', width: of(extra) },
        { part: 'moved-in', width: of(movedIn) },
      ] as BarPart[]
    ).filter((p) => p.width > 0),
    movedOut: Math.min(of(movedOut), 100),
    base: formatMoney(label.allocation),
    extra: formatMoney(label.addition),
    movedIn: formatMoney(label.transfer_in),
    movedOutText: movedOut ? `−${formatMoney(label.transfer_out)}` : formatMoney('0'),
  };
}

/** Totals, donut slices and sorted bars of a report summary. */
export function buildReportView(summary: ReportSummary): ReportView {
  const byKind = summary.by_kind as Record<Kind, string>;
  const withMoney = summary.labels.filter(
    (label) => cents(label.total) !== 0 || cents(label.transfer_out) !== 0,
  );
  const gross = (l: ReportLabel) => cents(l.allocation) + cents(l.addition) + cents(l.transfer_in);
  const largest = Math.max(0, ...withMoney.map(gross));
  return {
    window: windowText(summary.start_month, summary.end_month),
    total: formatMoney(summary.total),
    spent: formatMoney(byKind.expense ?? '0'),
    saved: formatMoney(byKind.saving ?? '0'),
    invested: formatMoney(byKind.investment ?? '0'),
    kindSegments: KIND_SEGMENTS.map(({ kind, label, pattern }) => ({
      key: kind,
      label,
      pattern,
      value: cents(byKind[kind] ?? '0'),
      color: `var(--kind-${kind})`,
      display: formatMoney(byKind[kind] ?? '0'),
    })),
    labelSegments: withMoney.map((label) => ({
      key: label.label_id,
      label: label.name,
      value: cents(label.total),
      color: label.color,
      display: formatMoney(label.total),
    })),
    bars: withMoney.map((label) => bar(label, largest)),
    empty: summary.labels.length - withMoney.length,
  };
}

export interface TrendView {
  points: LinePoint[];
  average: string;
  highest: string;
  highestMonth: string;
  aria: string;
}

/** The selected labels combined, month by month; null when there is under two months. */
export function buildTrend(series: ReportSeries): TrendView | null {
  if (series.totals.length < 2) return null;
  const years = new Set(series.months.map((m) => m.slice(0, 4)));
  const values = series.totals.map((p) => cents(p.total));
  const points = series.totals.map((p, i) => ({
    key: p.month,
    label: monthLabel(p.month, years.size > 1 && (i === 0 || p.month.endsWith('-01'))),
    value: values[i]! / 100,
    display: formatMoney(p.total),
  }));
  const top = values.indexOf(Math.max(...values));
  return {
    points,
    average: formatMoney(fromCents(Math.round(values.reduce((a, b) => a + b, 0) / values.length))),
    highest: points[top]!.display,
    highestMonth: monthLabel(series.months[top]!, true),
    aria: `Selected labels per month: ${points.map((p) => `${p.label} ${p.display}`).join(', ')}`,
  };
}

export interface EntryRow {
  id: string;
  date: string;
  label: string;
  color: string;
  origin: string;
  amount: string;
  /** Money that left the label (a transfer out), shown with a minus sign. */
  outgoing: boolean;
}

export interface LabelInfo {
  name: string;
  color: string;
}

function longDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year!, month! - 1, day!).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/** Report entries as rows. Each transfer leg is shown from its own label's side. */
export function entryRows(entries: ReportEntry[], labels: Map<string, LabelInfo>): EntryRow[] {
  const info = (id: string | null | undefined): LabelInfo =>
    (id && labels.get(id)) || { name: 'Deleted label', color: 'var(--color-border-strong)' };
  return entries.map((entry) => {
    const label = info(entry.label_id);
    const money = formatMoney(entry.amount);
    const row = {
      id: entry.id,
      date: longDate(entry.occurred_on),
      label: label.name,
      color: label.color,
    };
    switch (entry.origin) {
      case 'transfer_out':
        return {
          ...row,
          origin: `Moved to ${info(entry.counterpart_label_id).name}`,
          amount: `−${money}`,
          outgoing: true,
        };
      case 'transfer_in':
        return {
          ...row,
          origin: `Moved from ${info(entry.counterpart_label_id).name}`,
          amount: `+${money}`,
          outgoing: false,
        };
      case 'external_income':
        return {
          ...row,
          origin:
            entry.source && entry.source !== 'Extra income'
              ? `Extra income · ${entry.source}`
              : 'Extra income',
          amount: `+${money}`,
          outgoing: false,
        };
      default:
        return { ...row, origin: 'Initial distribution', amount: money, outgoing: false };
    }
  });
}
