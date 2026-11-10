import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import {
  LabelKind,
  LabelRead,
  ReportEntry,
  ReportPeriod,
  ReportSeries,
  ReportSummary,
} from '../../core/api/types';
import { exportErrorMessage, ExportsService } from '../../core/exports/exports.service';
import { readPreference, writePreference } from '../../core/storage/preferences';
import { Donut } from '../../shared/charts/donut';
import { LineChart } from '../../shared/charts/line-chart';
import { wholeEuros } from '../../shared/charts/month-label';
import { KIND_NAMES, KINDS } from '../../shared/money/kind';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { LabelsApi } from '../labels/labels-api';
import { ReportFilter, ReportsApi } from './reports-api';
import { buildReportView, buildTrend, entryRows, LabelInfo, REPORT_PERIODS } from './report-view';

type LoadState = 'loading' | 'ready' | 'error';
type DonutMode = 'overview' | 'detailed';
type BarsMode = 'chart' | 'table';

const DEFAULT_PERIOD: ReportPeriod = 'last_6_months';
const PAGE_SIZE = 50;
const DONUT_MODE_KEY = 'fs.reports.donut';
const BARS_MODE_KEY = 'fs.reports.bars';

/** A query parameter that may be absent, given once, or repeated. */
type QueryValue = string | string[] | undefined;
const many = (value: QueryValue): string[] =>
  value === undefined ? [] : Array.isArray(value) ? value : [value];

/**
 * Totals, distribution, evolution and entries for any period and mix of labels
 * and kinds. The filters live in the URL (?period=&kind=&label=), so a report
 * can be bookmarked or shared.
 */
@Component({
  selector: 'app-reports-page',
  imports: [CdkMenu, CdkMenuItem, CdkMenuTrigger, Donut, Icon, LineChart],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './reports-page.html',
  styleUrl: './reports-page.scss',
})
export default class ReportsPage {
  private readonly api = inject(ReportsApi);
  private readonly labelsApi = inject(LabelsApi);
  private readonly router = inject(Router);
  private readonly exports = inject(ExportsService);
  private readonly toasts = inject(ToastService);
  protected readonly exporting = this.exports.busy;

  /** Query params (withComponentInputBinding). */
  readonly period = input<QueryValue>();
  readonly kind = input<QueryValue>();
  readonly label = input<QueryValue>();

  protected readonly periods = REPORT_PERIODS;
  protected readonly kinds = KINDS.map((kind) => ({ kind, text: KIND_NAMES[kind] }));
  protected readonly formatAxis = wholeEuros;

  protected readonly activePeriod = computed<ReportPeriod>(
    () => REPORT_PERIODS.find((p) => p.value === this.period())?.value ?? DEFAULT_PERIOD,
  );
  protected readonly selectedKinds = computed(() =>
    many(this.kind()).filter((k): k is LabelKind => (KINDS as readonly string[]).includes(k)),
  );
  protected readonly selectedLabels = computed(() => many(this.label()));
  protected readonly filtered = computed(
    () => this.selectedKinds().length > 0 || this.selectedLabels().length > 0,
  );
  private readonly filter = computed<ReportFilter>(() => ({
    period: this.activePeriod(),
    kinds: this.selectedKinds(),
    labelIds: this.selectedLabels(),
  }));

  protected readonly labels = signal<LabelRead[]>([]);
  protected readonly state = signal<LoadState>('loading');
  private readonly summary = signal<ReportSummary | null>(null);
  private readonly series = signal<ReportSeries | null>(null);
  private readonly entries = signal<ReportEntry[]>([]);
  protected readonly entryCount = signal(0);
  protected readonly loadingMore = signal(false);
  private readonly reloads = signal(0);

  protected readonly donutMode = signal<DonutMode>(
    readPreference(DONUT_MODE_KEY) === 'detailed' ? 'detailed' : 'overview',
  );
  protected readonly barsMode = signal<BarsMode>(
    readPreference(BARS_MODE_KEY) === 'table' ? 'table' : 'chart',
  );

  /** Labels to pick from: the active ones, plus any archived one already in the URL. */
  protected readonly labelOptions = computed(() => {
    const chosen = new Set(this.selectedLabels());
    return this.labels().filter((label) => !label.archived_at || chosen.has(label.id));
  });

  protected readonly view = computed(() => {
    const summary = this.summary();
    return summary ? buildReportView(summary) : null;
  });
  protected readonly trend = computed(() => {
    const series = this.series();
    return series ? buildTrend(series) : null;
  });
  protected readonly rows = computed(() => {
    const names = new Map<string, LabelInfo>(
      this.labels().map((label) => [label.id, { name: label.name, color: label.color }]),
    );
    // Deleted labels with history come only in the summary.
    for (const label of this.summary()?.labels ?? []) {
      if (!names.has(label.label_id)) {
        names.set(label.label_id, { name: label.name, color: label.color });
      }
    }
    return entryRows(this.entries(), names);
  });

  constructor() {
    this.labelsApi.list(true).subscribe({ next: (labels) => this.labels.set(labels) });
    effect((onCleanup) => {
      const filter = this.filter();
      this.reloads();
      this.state.set('loading');
      const request = forkJoin({
        summary: this.api.summary(filter),
        series: this.api.series(filter),
        entries: this.api.entries(filter, { limit: PAGE_SIZE, offset: 0 }),
      }).subscribe({
        next: ({ summary, series, entries }) => {
          this.summary.set(summary);
          this.series.set(series);
          this.entries.set(entries.entries);
          this.entryCount.set(entries.count);
          this.state.set('ready');
        },
        error: () => this.state.set('error'),
      });
      onCleanup(() => request.unsubscribe());
    });
  }

  /** Exports this report's entries (same period and categories) as CSV or PDF. */
  protected exportAs(format: 'csv' | 'pdf'): void {
    const filter = this.filter();
    this.toasts.show(`Preparing the ${format.toUpperCase()}…`);
    this.exports
      .report({
        format,
        period: this.activePeriod(),
        kinds: [...(filter.kinds ?? [])],
        label_ids: [...(filter.labelIds ?? [])],
      })
      .subscribe({
        next: (done) => this.toasts.show(`${done.filename} downloaded`),
        error: (error: unknown) => this.toasts.show(exportErrorMessage(error)),
      });
  }

  protected setPeriod(period: ReportPeriod): void {
    this.navigate({ period: period === DEFAULT_PERIOD ? null : period });
  }

  protected toggleKind(kind: LabelKind): void {
    this.navigate({ kind: toggle(this.selectedKinds(), kind) });
  }

  protected toggleLabel(id: string): void {
    this.navigate({ label: toggle(this.selectedLabels(), id) });
  }

  protected clearFilters(): void {
    this.navigate({ kind: null, label: null });
  }

  protected retry(): void {
    this.reloads.update((n) => n + 1);
  }

  protected loadMore(): void {
    this.loadingMore.set(true);
    this.api.entries(this.filter(), { limit: PAGE_SIZE, offset: this.entries().length }).subscribe({
      next: (page) => {
        this.entries.update((current) => [...current, ...page.entries]);
        this.entryCount.set(page.count);
        this.loadingMore.set(false);
      },
      error: () => this.loadingMore.set(false),
    });
  }

  protected setDonutMode(mode: DonutMode): void {
    this.donutMode.set(mode);
    writePreference(DONUT_MODE_KEY, mode === 'overview' ? null : mode);
  }

  protected setBarsMode(mode: BarsMode): void {
    this.barsMode.set(mode);
    writePreference(BARS_MODE_KEY, mode === 'chart' ? null : mode);
  }

  protected isKindOn(kind: LabelKind): boolean {
    return this.selectedKinds().includes(kind);
  }

  protected isLabelOn(id: string): boolean {
    return this.selectedLabels().includes(id);
  }

  private navigate(queryParams: Record<string, unknown>): void {
    void this.router.navigate([], { queryParams, queryParamsHandling: 'merge', replaceUrl: true });
  }
}

function toggle<T>(list: readonly T[], value: T): T[] | null {
  const next = list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
  return next.length ? next : null;
}
