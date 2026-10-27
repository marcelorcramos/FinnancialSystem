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
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { MonthRead } from '../../core/api/types';
import { Donut } from '../../shared/charts/donut';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { monthPath, monthTitle, shiftMonth } from './month-route';
import { buildMonthView, MonthView } from './month-view';
import { MonthsApi } from './months-api';

type LoadState = 'loading' | 'ready' | 'missing' | 'error';

@Component({
  selector: 'app-month-page',
  imports: [Donut, Icon, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './month-page.html',
  styleUrl: './month-page.scss',
})
export default class MonthPage {
  private readonly api = inject(MonthsApi);
  private readonly toasts = inject(ToastService);

  /** Route params (withComponentInputBinding). */
  readonly year = input.required({ transform: numberAttribute });
  readonly month = input.required({ transform: numberAttribute });

  protected readonly state = signal<LoadState>('loading');
  protected readonly sheet = signal<MonthRead | null>(null);
  protected readonly view = signal<MonthView | null>(null);
  protected readonly showAllLabels = signal(false);
  protected readonly creating = signal(false);

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

  protected reload(): void {
    this.load(this.year(), this.month());
  }

  /** Creates an empty sheet; copying the previous month comes with the New month dialog. */
  protected createMonth(): void {
    this.creating.set(true);
    this.api
      .create({
        year: this.year(),
        month: this.month(),
        copy_allocations: false,
        copy_incomes: false,
      })
      .subscribe({
        next: () => {
          this.creating.set(false);
          this.reload();
        },
        error: (error: unknown) => {
          this.creating.set(false);
          this.toasts.show(apiErrorMessage(error));
        },
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
