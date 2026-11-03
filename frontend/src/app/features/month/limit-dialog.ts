import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { LimitRead } from '../../core/api/types';
import { fromCents, toCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { Icon } from '../../shared/ui/icon';
import { LimitsApi } from './limits-api';

export interface LimitDialogData {
  monthId: string;
  monthTitle: string;
  labelId: string;
  labelName: string;
  total: string;
}

type Scope = 'default' | 'month';

/**
 * Sets a label's limit: for every month (its default) or only for this month.
 * Limits only warn (alerts at 80% and 100%); they never block.
 */
@Component({
  selector: 'app-limit-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './limit-dialog.html',
  styleUrl: './add-money-dialog.scss',
})
export class LimitDialog {
  private readonly api = inject(LimitsApi);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  protected readonly data = inject<LimitDialogData>(DIALOG_DATA);

  protected readonly defaultLimit = signal<LimitRead | null>(null);
  protected readonly monthLimit = signal<LimitRead | null>(null);
  protected readonly loading = signal(true);
  protected readonly scope = signal<Scope>('default');
  protected readonly amountText = signal('');
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly cents = computed(() => toCents(this.amountText()));
  protected readonly current = computed(() =>
    this.scope() === 'month' ? this.monthLimit() : this.defaultLimit(),
  );
  protected readonly preview = computed(() => {
    const limit = this.cents();
    const total = toCents(this.data.total) ?? 0;
    if (!limit) return null;
    const percent = Math.round((Math.max(total, 0) / limit) * 1000) / 10;
    return `${formatMoney(this.data.total)} of ${formatMoney(fromCents(limit))} this month · ${percent}%`;
  });
  protected readonly money = formatMoney;

  constructor() {
    this.api.list().subscribe({
      next: (limits) => {
        const mine = limits.filter((l) => l.label_id === this.data.labelId);
        const def = mine.find((l) => l.month_id === null) ?? null;
        const month = mine.find((l) => l.month_id === this.data.monthId) ?? null;
        this.defaultLimit.set(def);
        this.monthLimit.set(month);
        this.scope.set(month ? 'month' : 'default');
        this.amountText.set((month ?? def)?.amount ?? '');
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.error.set(apiErrorMessage(error));
        this.loading.set(false);
      },
    });
  }

  protected setScope(scope: Scope): void {
    this.scope.set(scope);
    const limit = scope === 'month' ? this.monthLimit() : this.defaultLimit();
    if (limit) this.amountText.set(limit.amount);
  }

  protected save(): void {
    const cents = this.cents();
    if (!cents || this.pending()) return;
    const monthId = this.scope() === 'month' ? this.data.monthId : null;
    this.run(this.api.set(this.data.labelId, fromCents(cents), monthId));
  }

  /** Removes the limit shown (this month's, so the default applies again, or the default). */
  protected remove(): void {
    const monthId = this.scope() === 'month' ? this.data.monthId : null;
    this.run(this.api.remove(this.data.labelId, monthId));
  }

  private run(request: Observable<unknown>): void {
    this.pending.set(true);
    this.error.set(null);
    request.subscribe({
      next: () => this.ref.close(true),
      error: (error: unknown) => {
        this.pending.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
