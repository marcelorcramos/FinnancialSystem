import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';

import { LabelKind, LabelSummary, ReportPeriod, ReportSeries } from '../../core/api/types';
import { readPreference, writePreference } from '../../core/storage/preferences';
import { LineChart, LinePoint } from '../../shared/charts/line-chart';
import { fromCents, signedCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { ReportsApi } from '../reports/reports-api';

type EvolutionPeriod = Extract<ReportPeriod, 'last_6_months' | 'last_12_months' | 'all'>;

export const EVOLUTION_PERIODS: { value: EvolutionPeriod; text: string }[] = [
  { value: 'last_6_months', text: 'Last 6 months' },
  { value: 'last_12_months', text: 'Last 12 months' },
  { value: 'all', text: 'All time' },
];

const KIND_GROUPS: { kind: LabelKind; text: string }[] = [
  { kind: 'expense', text: 'Expense' },
  { kind: 'saving', text: 'Saving' },
  { kind: 'investment', text: 'Investment' },
];

const LABEL_KEY = 'fs.month.evolution.label';
const PERIOD_KEY = 'fs.month.evolution.period';
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-05" -> "May"; the year is added when the series crosses one ("Jan 27"). */
function monthLabel(key: string, withYear: boolean): string {
  const [year, month] = key.split('-');
  const name = MONTHS[Number(month) - 1]!;
  return withYear ? `${name} ${year!.slice(2)}` : name;
}

function wholeEuros(value: number): string {
  const euros = Math.round(Math.abs(value));
  return `${value < 0 ? '−' : ''}€${euros.toLocaleString('en-IE')}`;
}

/**
 * How one label moved across months (line chart), with a category and a
 * period selector. Windows are rolling from the current month, like reports.
 */
@Component({
  selector: 'app-evolution',
  imports: [LineChart],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './evolution.html',
  styleUrl: './evolution.scss',
})
export class Evolution {
  private readonly api = inject(ReportsApi);

  /** Labels to choose from (the month summary's), and the one to start with. */
  readonly labels = input.required<LabelSummary[]>();
  readonly preferred = input<string | null>(null);
  /** Any new value refetches the series (e.g. after money moved). */
  readonly refresh = input<unknown>();

  protected readonly periods = EVOLUTION_PERIODS;
  protected readonly formatAxis = wholeEuros;
  private readonly chosen = signal<string | null>(readPreference(LABEL_KEY));
  protected readonly period = signal<EvolutionPeriod>(
    EVOLUTION_PERIODS.find((p) => p.value === readPreference(PERIOD_KEY))?.value ?? 'last_6_months',
  );
  protected readonly series = signal<ReportSeries | null>(null);
  protected readonly failed = signal(false);

  protected readonly options = computed(() => {
    const usable = this.labels().filter((label) => !label.archived);
    return KIND_GROUPS.map((group) => ({
      ...group,
      labels: usable.filter((label) => label.kind === group.kind),
    })).filter((group) => group.labels.length);
  });

  protected readonly selected = computed(() => {
    const usable = this.labels().filter((label) => !label.archived);
    const find = (id: string | null) => usable.find((label) => label.label_id === id);
    return find(this.chosen()) ?? find(this.preferred()) ?? usable[0] ?? null;
  });

  protected readonly view = computed(() => {
    const series = this.series();
    const label = this.selected();
    const row = series?.labels.find((l) => l.label_id === label?.label_id);
    if (!series || !label || !row || !row.points.length) return null;

    const years = new Set(series.months.map((m) => m.slice(0, 4)));
    const cents = row.points.map((p) => signedCents(p.total) ?? 0);
    const points: LinePoint[] = row.points.map((p, i) => ({
      key: p.month,
      label: monthLabel(p.month, years.size > 1 && (i === 0 || p.month.endsWith('-01'))),
      value: cents[i]! / 100,
      display: formatMoney(p.total),
    }));
    const first = cents[0]!;
    const last = cents.at(-1)!;
    const average = Math.round(cents.reduce((a, b) => a + b, 0) / cents.length);
    const periodText =
      this.period() === 'all'
        ? `since ${monthLabel(series.months[0]!, true)}`
        : `over the ${EVOLUTION_PERIODS.find((p) => p.value === this.period())!.text.toLowerCase()}`;

    return {
      points,
      color: label.color,
      current: points.at(-1)!.display,
      average: formatMoney(fromCents(average)),
      changeLabel: `vs. ${points[0]!.label}`,
      change:
        first === 0
          ? last === 0
            ? '—'
            : 'New'
          : `${last >= first ? '+' : '−'}${Math.abs(((last - first) / Math.abs(first)) * 100).toFixed(1)}%`,
      aria: `${label.name} ${periodText}: ${points.map((p) => `${p.label} ${p.display}`).join(', ')}`,
    };
  });

  constructor() {
    effect((onCleanup) => {
      const label = this.selected();
      const period = this.period();
      this.refresh();
      if (!label) return;
      this.failed.set(false);
      const request = this.api.series({ period, labelIds: [label.label_id] }).subscribe({
        next: (series) => this.series.set(series),
        error: () => this.failed.set(true),
      });
      onCleanup(() => request.unsubscribe());
    });
  }

  protected pickLabel(id: string): void {
    this.chosen.set(id);
    writePreference(LABEL_KEY, id);
  }

  protected pickPeriod(value: string): void {
    const period = EVOLUTION_PERIODS.find((p) => p.value === value)?.value ?? 'last_6_months';
    this.period.set(period);
    writePreference(PERIOD_KEY, period === 'last_6_months' ? null : period);
  }
}
