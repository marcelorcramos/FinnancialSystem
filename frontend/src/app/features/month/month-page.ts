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

import { apiErrorMessage } from '../../core/api/api-errors';
import { EntryListItem, MonthRead, MonthSummary } from '../../core/api/types';
import { readPreference, writePreference } from '../../core/storage/preferences';
import { Donut } from '../../shared/charts/donut';
import { Evolution } from './evolution';
import { QuickEntry } from './quick-entry';
import { dialogA11y } from '../../shared/ui/dialog-a11y';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { AddMoneyData, AddMoneyDialog } from './add-money-dialog';
import { NewMonthData, NewMonthDialog } from './new-month-dialog';
import { PlanMonthData, PlanMonthDialog } from './plan-month-dialog';
import { monthPath, monthTitle, shiftMonth } from './month-route';
import { buildMonthView, MonthView, RecentEntry } from './month-view';
import { MonthsApi } from './months-api';

type LoadState = 'loading' | 'ready' | 'missing' | 'error';

/** Donut view: one slice per kind, or one slice per label. */
export type DonutMode = 'overview' | 'detailed';
const DONUT_MODE_KEY = 'fs.month.donut';

@Component({
  selector: 'app-month-page',
  imports: [Donut, Evolution, Icon, QuickEntry, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './month-page.html',
  styleUrl: './month-page.scss',
  host: { '(document:keydown)': 'onKeydown($event)' },
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
  protected readonly summary = signal<MonthSummary | null>(null);
  private readonly entries = signal<EntryListItem[]>([]);
  protected readonly showAllLabels = signal(false);
  protected readonly showAllEntries = signal(false);
  protected readonly view = computed<MonthView | null>(() => {
    const summary = this.summary();
    if (!summary) return null;
    return buildMonthView(summary, this.entries(), this.showAllEntries() ? Infinity : 6);
  });
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

  /**
   * Shortcuts (listed on the Preferences page): N new entry, T transfer,
   * ←/→ previous/next month, ⌘/Ctrl+Z undo the last delete. Ignored while
   * typing in a field or with a dialog open.
   */
  protected onKeydown(event: KeyboardEvent): void {
    const target = event.target as HTMLElement | null;
    const typing =
      !!target?.closest('input, select, textarea, [contenteditable="true"]') ||
      this.dialog.openDialogs.length > 0;
    if (event.defaultPrevented || typing || event.altKey) return;

    const key = event.key.toLowerCase();
    if (key === 'z' && (event.metaKey || event.ctrlKey) && !event.shiftKey) {
      if (this.toasts.undoLatest()) event.preventDefault();
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey) return;

    const focus = (selector: string) => {
      const field = document.querySelector<HTMLElement>(selector);
      if (!field) return;
      event.preventDefault();
      field.focus();
    };
    if (key === 'n') focus('#quick-amount');
    else if (key === 't') focus('#quick-from');
    else if (key === 'arrowleft') void this.router.navigateByUrl(this.previous().path);
    else if (key === 'arrowright') void this.router.navigateByUrl(this.next().path);
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
      .open<boolean, AddMoneyData>(AddMoneyDialog, {
        data: { summary, labelId },
        ...dialogA11y('add-money-title'),
      })
      .closed.subscribe((done) => {
        if (!done) return;
        this.toasts.show('Money added');
        this.reload();
      });
  }

  /** After a quick entry: confirm it and show the new totals. */
  protected entryAdded(description: string): void {
    this.toasts.show(description);
    this.reload();
  }

  /** Edits the month's recurring incomes and the initial distribution per label. */
  protected plan(): void {
    const summary = this.summary();
    if (!summary) return;
    this.dialog
      .open<boolean, PlanMonthData>(PlanMonthDialog, {
        data: { summary },
        ...dialogA11y('plan-title'),
      })
      .closed.subscribe((saved) => {
        if (!saved) return;
        this.toasts.show('Plan saved');
        this.reload();
      });
  }

  /** Deletes an entry (soft delete) and offers to bring it back. */
  protected deleteEntry(entry: RecentEntry): void {
    this.api.deleteEntry(entry.id).subscribe({
      next: () => {
        this.toasts.show(`“${entry.title}” deleted`, {
          label: 'Undo',
          run: () =>
            this.api.restoreEntry(entry.id).subscribe({
              next: () => this.reload(),
              error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
            }),
        });
        this.reload();
      },
      error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
    });
  }

  /** Closes the month (no more changes) or reopens it. */
  protected setClosed(closed: boolean): void {
    const sheet = this.sheet();
    if (!sheet) return;
    const request = closed ? this.api.close(sheet.id) : this.api.reopen(sheet.id);
    request.subscribe({
      next: () => {
        const title = this.title();
        if (closed) {
          this.toasts.show(`${title} closed`, { label: 'Undo', run: () => this.setClosed(false) });
        } else {
          this.toasts.show(`${title} reopened`);
        }
        this.reload();
      },
      error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
    });
  }

  /** Opens the New month dialog for this month, or for the one after it. */
  protected newMonth(which: 'this' | 'next'): void {
    const target =
      which === 'this'
        ? { year: this.year(), month: this.month() }
        : shiftMonth(this.year(), this.month(), 1);
    this.dialog
      .open<MonthRead, NewMonthData>(NewMonthDialog, {
        data: target,
        ...dialogA11y('new-month-title'),
      })
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
    this.showAllEntries.set(false);
    this.api.find(year, month).subscribe({
      next: (sheet) => {
        this.sheet.set(sheet);
        if (!sheet) {
          this.summary.set(null);
          this.state.set('missing');
          return;
        }
        forkJoin([this.api.summary(sheet.id), this.api.entries(sheet.id)]).subscribe({
          next: ([summary, entries]) => {
            this.entries.set(entries);
            this.summary.set(summary);
            this.state.set('ready');
          },
          error: () => this.state.set('error'),
        });
      },
      error: () => this.state.set('error'),
    });
  }
}
