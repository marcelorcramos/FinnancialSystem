import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { LabelSummary, MonthSummary } from '../../core/api/types';
import { fromCents, signedCents, toCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { Icon } from '../../shared/ui/icon';
import { MonthsApi } from './months-api';

export interface AddMoneyData {
  summary: MonthSummary;
  /** Label to add money to; the first usable label when absent. */
  labelId?: string;
}

type Origin = 'outside' | 'label';

/** Default date: today when it falls in the month, else the month's first day. */
export function defaultDate(year: number, month: number, today = new Date()): string {
  const inMonth = today.getFullYear() === year && today.getMonth() + 1 === month;
  const day = inMonth ? today.getDate() : 1;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/**
 * Adds money to a label. From outside the app it is an addition (the month's
 * income rises too); from another label it is a transfer (income unchanged).
 * The effect is shown before confirming.
 */
@Component({
  selector: 'app-add-money-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './add-money-dialog.html',
  styleUrl: './add-money-dialog.scss',
})
export class AddMoneyDialog {
  private readonly api = inject(MonthsApi);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  protected readonly data = inject<AddMoneyData>(DIALOG_DATA);

  protected readonly labels: LabelSummary[] = this.data.summary.labels.filter((l) => !l.archived);
  protected readonly targetId = signal(this.data.labelId ?? this.labels[0]?.label_id ?? '');
  protected readonly amountText = signal('');
  protected readonly date = signal(defaultDate(this.data.summary.year, this.data.summary.month));
  protected readonly origin = signal<Origin>('outside');
  protected readonly source = signal('');
  protected readonly fromId = signal(
    this.labels.find((l) => l.label_id !== this.targetId())?.label_id ?? '',
  );
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly target = computed(() => this.byId(this.targetId()));
  protected readonly sources = computed(() =>
    this.labels.filter((l) => l.label_id !== this.targetId()),
  );
  protected readonly cents = computed(() => toCents(this.amountText()));
  protected readonly valid = computed(
    () =>
      !!this.target() &&
      (this.cents() ?? 0) > 0 &&
      (this.origin() === 'outside' || !!this.byId(this.fromId())),
  );

  /** Before → after lines for the confirmation panel. */
  protected readonly impact = computed(() => {
    const amount = this.cents() ?? 0;
    const line = (name: string, before: string, delta: number) => {
      const signed = signedCents(before) ?? 0;
      const from = formatMoney(fromCents(signed));
      const to = formatMoney(fromCents(signed + delta));
      return {
        name,
        before: from,
        after: to,
        tone: delta > 0 ? 'up' : delta < 0 ? 'down' : 'same',
        sentence: `${name}: from ${from} to ${to}`,
      };
    };
    const lines = [];
    const target = this.target();
    if (target) lines.push(line(target.name, target.total, amount));
    if (this.origin() === 'outside') {
      lines.push(line('Month income', this.data.summary.income_total, amount));
    } else {
      const from = this.byId(this.fromId());
      if (from) lines.push(line(from.name, from.total, -amount));
    }
    const unallocated = line('Unallocated', this.data.summary.unallocated, 0);
    lines.push({
      ...unallocated,
      after: 'unchanged',
      sentence: `Unallocated: stays ${unallocated.before}`,
    });
    return lines;
  });

  protected readonly submitLabel = computed(() => {
    const amount = this.cents();
    const money = amount ? formatMoney(fromCents(amount)) : '';
    return this.origin() === 'outside' ? `Add ${money}`.trim() : `Move ${money}`.trim();
  });

  protected setTarget(id: string): void {
    this.targetId.set(id);
    if (this.fromId() === id) {
      this.fromId.set(this.sources()[0]?.label_id ?? '');
    }
  }

  protected submit(): void {
    if (this.pending() || !this.valid()) return;
    const monthId = this.data.summary.month_id;
    const amount = fromCents(this.cents()!);
    const request: Observable<unknown> =
      this.origin() === 'outside'
        ? this.api.addMoney(monthId, {
            label_id: this.targetId(),
            amount,
            occurred_on: this.date(),
            source: this.source().trim() || null,
          })
        : this.api.transfer(monthId, {
            from_label_id: this.fromId(),
            to_label_id: this.targetId(),
            amount,
            occurred_on: this.date(),
          });
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

  private byId(id: string): LabelSummary | undefined {
    return this.labels.find((l) => l.label_id === id);
  }
}
