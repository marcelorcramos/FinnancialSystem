import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { concat, Observable, toArray } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { MonthSummary } from '../../core/api/types';
import { fromCents, toCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { monthTitle } from './month-route';
import { MonthsApi } from './months-api';

export interface PlanMonthData {
  summary: MonthSummary;
}

/** A recurring income of the month; `id` is null for one added in this dialog. */
interface IncomeRow {
  key: string;
  id: string | null;
  source: string;
  savedSource: string;
  savedCents: number;
  text: string;
  removed: boolean;
}

/** One label's initial distribution for the month. */
interface AllocationRow {
  id: string;
  name: string;
  color: string;
  icon: IconName;
  savedCents: number;
  text: string;
}

/** Extra income from "Add money": shown for the total, edited through its entry. */
interface ExtraIncome {
  source: string;
  cents: number;
}

const STEP_CENTS = 1000;

/**
 * Plans an existing month: its recurring incomes (salary...) and how much each
 * label gets at the start. Totals update while typing; saving sends only what
 * changed.
 */
@Component({
  selector: 'app-plan-month-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './plan-month-dialog.html',
  styleUrls: ['./new-month-dialog.scss', './plan-month-dialog.scss'],
})
export class PlanMonthDialog implements OnInit {
  private readonly api = inject(MonthsApi);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  private readonly summary = inject<PlanMonthData>(DIALOG_DATA).summary;

  protected readonly title = monthTitle(this.summary.year, this.summary.month);
  protected readonly loading = signal(true);
  protected readonly incomes = signal<IncomeRow[]>([]);
  protected readonly extras = signal<ExtraIncome[]>([]);
  protected readonly allocations = signal<AllocationRow[]>(
    this.summary.labels
      .filter((label) => !label.archived)
      .map((label) => {
        const cents = toCents(label.allocation) ?? 0;
        return {
          id: label.label_id,
          name: label.name,
          color: label.color,
          icon: isIconName(label.icon) ? label.icon : 'labels',
          savedCents: cents,
          text: fromCents(cents),
        };
      }),
  );
  protected readonly extrasTotal = computed(() =>
    this.extras().reduce((sum, extra) => sum + extra.cents, 0),
  );
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  private nextKey = 0;

  protected readonly invalid = computed(
    () =>
      this.incomes().some(
        (row) => !row.removed && (!(toCents(row.text)! > 0) || !row.source.trim()),
      ) || this.allocations().some((row) => toCents(row.text) === null),
  );
  protected readonly changes = computed(
    () =>
      this.incomes().filter((row) => this.incomeChanged(row)).length +
      this.allocations().filter((row) => toCents(row.text) !== row.savedCents).length,
  );
  protected readonly totals = computed(() => {
    const income =
      this.incomes().reduce(
        (sum, row) => sum + (row.removed ? 0 : (toCents(row.text) ?? row.savedCents)),
        0,
      ) + this.extrasTotal();
    const distributed = this.allocations().reduce(
      (sum, row) => sum + (toCents(row.text) ?? row.savedCents),
      0,
    );
    return {
      income: formatMoney(fromCents(income)),
      distributed: formatMoney(fromCents(distributed)),
      unallocated: formatMoney(fromCents(income - distributed)),
      negative: income - distributed < 0,
    };
  });

  ngOnInit(): void {
    this.api.incomes(this.summary.month_id).subscribe({
      next: (incomes) => {
        this.incomes.set(
          incomes
            .filter((income) => !income.from_addition)
            .map((income) => {
              const cents = toCents(income.amount) ?? 0;
              return {
                key: income.id,
                id: income.id,
                source: income.source,
                savedSource: income.source,
                savedCents: cents,
                text: fromCents(cents),
                removed: false,
              };
            }),
        );
        this.extras.set(
          incomes
            .filter((income) => income.from_addition)
            .map((income) => ({ source: income.source, cents: toCents(income.amount) ?? 0 })),
        );
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.loading.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }

  protected money(cents: number): string {
    return formatMoney(fromCents(cents));
  }

  protected addIncome(): void {
    const first = !this.incomes().some((row) => !row.removed);
    this.incomes.update((rows) => [
      ...rows,
      {
        key: `new-${this.nextKey++}`,
        id: null,
        source: first ? 'Salary' : '',
        savedSource: '',
        savedCents: 0,
        text: '',
        removed: false,
      },
    ]);
  }

  protected editIncome(key: string, change: Partial<Pick<IncomeRow, 'source' | 'text'>>): void {
    this.incomes.update((rows) =>
      rows.map((row) => (row.key === key ? { ...row, ...change } : row)),
    );
  }

  /** New rows disappear; saved ones are marked and can be brought back. */
  protected toggleIncome(key: string): void {
    this.incomes.update((rows) =>
      rows.flatMap((row) => {
        if (row.key !== key) return [row];
        return row.id === null ? [] : [{ ...row, removed: !row.removed }];
      }),
    );
  }

  protected step(id: string, direction: 1 | -1): void {
    this.updateAllocation(id, (row) => {
      const base = toCents(row.text) ?? row.savedCents;
      return { ...row, text: fromCents(Math.max(0, base + direction * STEP_CENTS)) };
    });
  }

  protected type(id: string, text: string): void {
    this.updateAllocation(id, (row) => ({ ...row, text }));
  }

  protected delta(row: AllocationRow): { text: string; tone: 'same' | 'changed' | 'removed' } {
    const cents = toCents(row.text);
    if (cents === null) return { text: 'Not an amount', tone: 'removed' };
    const diff = cents - row.savedCents;
    if (diff === 0) return { text: '', tone: 'same' };
    const sign = diff > 0 ? '+' : '−';
    return { text: `${sign}${this.money(Math.abs(diff))} not saved yet`, tone: 'changed' };
  }

  protected save(): void {
    if (this.pending() || this.invalid()) return;
    if (!this.changes()) {
      this.ref.close(false);
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    const calls = [...this.incomeCalls(), ...this.allocationCalls()];
    concat(...calls)
      .pipe(toArray())
      .subscribe({
        next: () => this.ref.close(true),
        error: (error: unknown) => {
          this.pending.set(false);
          this.error.set(apiErrorMessage(error));
        },
      });
  }

  private incomeChanged(row: IncomeRow): boolean {
    if (row.id === null) return !row.removed;
    return (
      row.removed || toCents(row.text) !== row.savedCents || row.source.trim() !== row.savedSource
    );
  }

  private incomeCalls(): Observable<unknown>[] {
    const { year, month } = this.summary;
    const firstDay = `${year}-${String(month).padStart(2, '0')}-01`;
    return this.incomes()
      .filter((row) => this.incomeChanged(row))
      .map((row) => {
        const amount = fromCents(toCents(row.text) ?? 0);
        const source = row.source.trim();
        if (row.id === null) {
          return this.api.addIncome(this.summary.month_id, {
            source,
            amount,
            received_on: firstDay,
          });
        }
        if (row.removed) return this.api.deleteIncome(row.id);
        return this.api.updateIncome(row.id, { source, amount });
      });
  }

  private allocationCalls(): Observable<unknown>[] {
    return this.allocations()
      .filter((row) => toCents(row.text) !== row.savedCents)
      .map((row) =>
        this.api.setAllocation(this.summary.month_id, row.id, {
          amount: fromCents(toCents(row.text)!),
        }),
      );
  }

  private updateAllocation(id: string, change: (row: AllocationRow) => AllocationRow): void {
    this.allocations.update((rows) => rows.map((row) => (row.id === id ? change(row) : row)));
  }
}
