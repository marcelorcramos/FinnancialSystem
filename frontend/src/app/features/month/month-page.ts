import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  numberAttribute,
  signal,
} from '@angular/core';
import { Dialog } from '@angular/cdk/dialog';
import { Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MonthRead, MonthSummary } from '../../core/api/types';
import { readPreference, writePreference } from '../../core/storage/preferences';
import { Donut } from '../../shared/charts/donut';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { AddMoneyData, AddMoneyDialog } from './add-money-dialog';
import { NewMonthData, NewMonthDialog } from './new-month-dialog';
import { monthPath, monthTitle, shiftMonth } from './month-route';
import { buildMonthView, MonthView } from './month-view';
import { MonthsApi } from './months-api';

type LoadState = 'loading' | 'ready' | 'missing' | 'error';

/** Donut view: one slice per kind, or one slice per label. */
export type DonutMode = 'overview' | 'detailed';
const DONUT_MODE_KEY = 'fs.month.donut';

@Component({
  selector: 'app-month-page',
  imports: [Donut, Icon, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './month-page.html',
  styleUrl: './month-page.scss',
})
export default class MonthPage {
  private readonly api = inject(MonthsApi);
  private readonly dialog = inject(Dialog);
  private readonly router = inject(Router);
  private readonly toasts = inject(ToastService);

  /** Route params (withComponentInputBinding). */
  readonly year = input.required({ transform: numberAttribute });
  readonly month = input.required({ transform: numberAttribute });

  protected readonly state = signal<LoadState>('loading');
  protected readonly sheet = signal<MonthRead | null>(null);
  protected readonly view = signal<MonthView | null>(null);
  private readonly summary = signal<MonthSummary | null>(null);
  protected readonly showAllLabels = signal(false);
  protected readonly donutMode = signal<DonutMode>(
    readPreference(DONUT_MODE_KEY) === 'detailed' ? 'detailed' : 'overview',
  );

  protected readonly title = computed(() => monthTitle(this.year(), this.month()));
  protected readonly previous = computed(() => this.link(-1));
  protected readonly next = computed(() => this.link(1));
  protected readonly visibleLabels = computed(() => {
    const labels = this.view()?.labels ?? [];
    return this.showAllLabels() ? labels : labels.slice(0, 6);
  });

  constructor() {
    effect(() => this.load(this.year(), this.month()));
  }

  protected iconOf(icon: string): IconName {
    return isIconName(icon) ? icon : 'labels';
  }

  protected setDonutMode(mode: DonutMode): void {
    this.donutMode.set(mode);
    writePreference(DONUT_MODE_KEY, mode === 'overview' ? null : mode);
  }

  protected reload(): void {
    this.load(this.year(), this.month());
  }

  /** Adds money to a label, from outside the app or from another label. */
  protected addMoney(labelId?: string): void {
    const summary = this.summary();
    if (!summary) return;
    this.dialog
      .open<boolean, AddMoneyData>(AddMoneyDialog, { data: { summary, labelId } })
      .closed.subscribe((done) => {
        if (!done) return;
        this.toasts.show('Money added');
        this.reload();
      });
  }

  /** Opens the New month dialog for this month, or for the one after it. */
  protected newMonth(which: 'this' | 'next'): void {
    const target =
      which === 'this'
        ? { year: this.year(), month: this.month() }
        : shiftMonth(this.year(), this.month(), 1);
    this.dialog
      .open<MonthRead, NewMonthData>(NewMonthDialog, { data: target })
      .closed.subscribe((created) => {
        if (!created) return;
        this.toasts.show(`${monthTitle(created.year, created.month)} created`);
        if (created.year === this.year() && created.month === this.month()) {
          this.reload();
        } else {
          void this.router.navigateByUrl(monthPath(created.year, created.month));
        }
      });
  }

  private link(delta: number): { path: string; label: string } {
    const target = shiftMonth(this.year(), this.month(), delta);
    return {
      path: monthPath(target.year, target.month),
      label: monthTitle(target.year, target.month),
    };
  }

  private load(year: number, month: number): void {
    this.state.set('loading');
    this.showAllLabels.set(false);
    this.api.find(year, month).subscribe({
      next: (sheet) => {
        this.sheet.set(sheet);
        if (!sheet) {
          this.view.set(null);
          this.state.set('missing');
          return;
        }
        forkJoin([this.api.summary(sheet.id), this.api.entries(sheet.id)]).subscribe({
          next: ([summary, entries]) => {
            this.summary.set(summary);
            this.view.set(buildMonthView(summary, entries));
            this.state.set('ready');
          },
          error: () => this.state.set('error'),
        });
      },
      error: () => this.state.set('error'),
    });
  }
}
