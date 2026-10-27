import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { concat, forkJoin, map, Observable, of, switchMap, toArray } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { IncomeRead, MonthRead } from '../../core/api/types';
import { fromCents, toCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { monthTitle } from './month-route';
import { MonthsApi } from './months-api';

export interface NewMonthData {
  year: number;
  month: number;
}

/** One amount copied from the previous month, editable before the month is created. */
interface ReviewRow {
  id: string;
  name: string;
  color?: string;
  icon?: IconName;
  previousCents: number;
  text: string;
  skipped: boolean;
}

const STEP_CENTS = 1000;

/**
 * Creates a month, optionally copying the previous month's allocations and
 * recurring incomes. "Review amounts" shows each copied value next to the
 * previous one so it can be nudged, typed, removed or reset before creating.
 */
@Component({
  selector: 'app-new-month-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './new-month-dialog.html',
  styleUrl: './new-month-dialog.scss',
})
export class NewMonthDialog implements OnInit {
  private readonly api = inject(MonthsApi);
  protected readonly ref = inject<DialogRef<MonthRead>>(DialogRef);
  protected readonly data = inject<NewMonthData>(DIALOG_DATA);

  protected readonly title = monthTitle(this.data.year, this.data.month);
  protected readonly loading = signal(true);
  protected readonly previous = signal<{ id: string; title: string } | null>(null);
  protected readonly allocations = signal<ReviewRow[]>([]);
  protected readonly incomes = signal<ReviewRow[]>([]);
  protected readonly copyAllocations = signal(true);
  protected readonly copyIncomes = signal(true);
  protected readonly reviewing = signal(false);
  protected readonly note = signal('');
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  private static cents(row: ReviewRow): number | null {
    return row.skipped ? 0 : toCents(row.text);
  }

  protected readonly previousTotal = computed(() =>
    this.allocations().reduce((sum, row) => sum + row.previousCents, 0),
  );
  protected readonly previousTotalText = computed(() =>
    formatMoney(fromCents(this.previousTotal())),
  );
  protected readonly changedCount = computed(
    () =>
      this.allocations().filter((row) => NewMonthDialog.cents(row) !== row.previousCents).length,
  );
  protected readonly invalid = computed(() =>
    [...this.allocations(), ...this.incomes()].some((row) => NewMonthDialog.cents(row) === null),
  );
  protected readonly totals = computed(() => {
    const sum = (rows: ReviewRow[]) =>
      rows.reduce((total, row) => total + (NewMonthDialog.cents(row) ?? row.previousCents), 0);
    const income = this.copyIncomes() ? sum(this.incomes()) : 0;
    const distributed = this.copyAllocations() ? sum(this.allocations()) : 0;
    return {
      income: formatMoney(fromCents(income)),
      distributed: formatMoney(fromCents(distributed)),
      unallocated: formatMoney(fromCents(income - distributed)),
      negative: income - distributed < 0,
    };
  });

  ngOnInit(): void {
    const { year, month } = this.data;
    forkJoin([this.api.list(year), this.api.list(year - 1)])
      .pipe(
        map(
          ([thisYear, lastYear]) =>
            [...thisYear, ...lastYear]
              .filter((m) => m.year * 12 + m.month < year * 12 + month)
              .sort((a, b) => b.year * 12 + b.month - (a.year * 12 + a.month))[0],
        ),
        switchMap((prev) =>
          prev
            ? forkJoin([of(prev), this.api.summary(prev.id), this.api.incomes(prev.id)])
            : of(null),
        ),
      )
      .subscribe({
        next: (result) => {
          this.loading.set(false);
          if (!result) {
            this.copyAllocations.set(false);
            this.copyIncomes.set(false);
            return;
          }
          const [prev, summary, incomes] = result;
          this.previous.set({ id: prev.id, title: monthTitle(prev.year, prev.month) });
          this.allocations.set(
            summary.labels
              .filter((label) => !label.archived && toCents(label.allocation)! > 0)
              .map((label) => this.row(label.label_id, label.name, label.allocation, label)),
          );
          this.incomes.set(
            incomes
              .filter((income) => !income.from_addition)
              .map((income) => this.row(income.id, income.source, income.amount)),
          );
          this.copyAllocations.set(this.allocations().length > 0);
          this.copyIncomes.set(this.incomes().length > 0);
        },
        error: () => this.loading.set(false),
      });
  }

  protected delta(row: ReviewRow): { text: string; tone: 'same' | 'changed' | 'removed' } {
    if (row.skipped) return { text: 'Not in the new month', tone: 'removed' };
    const cents = toCents(row.text);
    if (cents === null) return { text: 'Not an amount', tone: 'removed' };
    const diff = cents - row.previousCents;
    if (diff === 0) return { text: 'Same as before', tone: 'same' };
    const sign = diff > 0 ? '+' : '−';
    return { text: `${sign}${formatMoney(fromCents(Math.abs(diff)))} vs. before`, tone: 'changed' };
  }

  protected previousOf(row: ReviewRow): string {
    return formatMoney(fromCents(row.previousCents));
  }

  protected step(list: 'allocations' | 'incomes', id: string, direction: 1 | -1): void {
    this.update(list, id, (row) => {
      const base = toCents(row.text) ?? row.previousCents;
      return {
        ...row,
        skipped: false,
        text: fromCents(Math.max(0, base + direction * STEP_CENTS)),
      };
    });
  }

  protected type(list: 'allocations' | 'incomes', id: string, text: string): void {
    this.update(list, id, (row) => ({ ...row, text }));
  }

  protected toggleSkip(id: string): void {
    this.update('allocations', id, (row) => ({ ...row, skipped: !row.skipped }));
  }

  protected reset(): void {
    const restore = (row: ReviewRow) => ({
      ...row,
      skipped: false,
      text: fromCents(row.previousCents),
    });
    this.allocations.update((rows) => rows.map(restore));
    this.incomes.update((rows) => rows.map(restore));
  }

  protected create(): void {
    if (this.pending() || this.invalid()) return;
    this.pending.set(true);
    this.error.set(null);
    const copyAllocations = this.copyAllocations() && this.allocations().length > 0;
    const copyIncomes = this.copyIncomes() && this.incomes().length > 0;
    this.api
      .create({
        year: this.data.year,
        month: this.data.month,
        note: this.note().trim() || null,
        copy_allocations: copyAllocations,
        copy_incomes: copyIncomes,
      })
      .pipe(
        switchMap((created) =>
          this.applyChanges(created, copyAllocations, copyIncomes).pipe(map(() => created)),
        ),
      )
      .subscribe({
        next: (created) => this.ref.close(created),
        error: (error: unknown) => {
          this.pending.set(false);
          this.error.set(apiErrorMessage(error));
        },
      });
  }

  /** Sends only what was reviewed: changed or removed allocations, changed incomes. */
  private applyChanges(
    created: MonthRead,
    copyAllocations: boolean,
    copyIncomes: boolean,
  ): Observable<unknown> {
    const calls: Observable<unknown>[] = [];
    if (copyAllocations) {
      for (const row of this.allocations()) {
        const cents = NewMonthDialog.cents(row)!;
        if (cents !== row.previousCents) {
          calls.push(this.api.setAllocation(created.id, row.id, { amount: fromCents(cents) }));
        }
      }
    }
    const changedIncomes = copyIncomes
      ? this.incomes().filter((row) => NewMonthDialog.cents(row) !== row.previousCents)
      : [];
    if (changedIncomes.length) {
      calls.push(
        this.api.incomes(created.id).pipe(
          switchMap((copied) => {
            const updates = this.incomeUpdates(copied, changedIncomes);
            return updates.length ? concat(...updates).pipe(toArray()) : of([]);
          }),
        ),
      );
    }
    return calls.length ? concat(...calls).pipe(toArray()) : of([]);
  }

  /** Matches each changed income with its copy (same source and previous amount). */
  private incomeUpdates(copied: IncomeRead[], changed: ReviewRow[]): Observable<IncomeRead>[] {
    const pool = [...copied];
    return changed.flatMap((row) => {
      const index = pool.findIndex(
        (income) => income.source === row.name && toCents(income.amount) === row.previousCents,
      );
      if (index < 0) return [];
      const [income] = pool.splice(index, 1);
      return [this.api.updateIncome(income!.id, { amount: fromCents(NewMonthDialog.cents(row)!) })];
    });
  }

  private row(
    id: string,
    name: string,
    amount: string,
    label?: { color: string; icon: string },
  ): ReviewRow {
    const cents = toCents(amount) ?? 0;
    return {
      id,
      name,
      color: label?.color,
      icon: label && isIconName(label.icon) ? label.icon : undefined,
      previousCents: cents,
      text: fromCents(cents),
      skipped: false,
    };
  }

  private update(
    list: 'allocations' | 'incomes',
    id: string,
    change: (row: ReviewRow) => ReviewRow,
  ) {
    this[list].update((rows) => rows.map((row) => (row.id === id ? change(row) : row)));
  }
}
