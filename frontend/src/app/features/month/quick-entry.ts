import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { MonthSummary } from '../../core/api/types';
import { fromCents, toCents } from '../../shared/money/cents';
import { formatMoney } from '../../shared/money/format-money';
import { defaultDate } from './add-money-dialog';
import { MonthsApi } from './months-api';

/** "From" value for money that comes from outside the app (an addition). */
export const OUTSIDE = 'outside';

/**
 * One-line entry on the month screen: an amount, the label it goes to and where
 * it comes from. From outside the app it is an addition; from another label, a
 * transfer. The Add money dialog stays for the date, source and the preview.
 */
@Component({
  selector: 'app-quick-entry',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="quick" aria-label="Quick entry" (submit)="$event.preventDefault(); submit()">
      <div class="field quick__amount">
        <label for="quick-amount">Amount</label>
        <input
          id="quick-amount"
          class="field__input num"
          inputmode="decimal"
          autocomplete="off"
          placeholder="0.00"
          [value]="amountText()"
          (input)="amountText.set($any($event.target).value)"
        />
      </div>
      <div class="field">
        <label for="quick-to">To</label>
        <select id="quick-to" class="field__input" (change)="setTarget($any($event.target).value)">
          @for (label of labels(); track label.label_id) {
            <option [value]="label.label_id" [selected]="label.label_id === targetId()">
              {{ label.name }}
            </option>
          }
        </select>
      </div>
      <div class="field">
        <label for="quick-from">From</label>
        <select
          id="quick-from"
          class="field__input"
          (change)="fromId.set($any($event.target).value)"
        >
          <option [value]="outside" [selected]="fromId() === outside">Outside the app</option>
          @for (label of sources(); track label.label_id) {
            <option [value]="label.label_id" [selected]="label.label_id === fromId()">
              {{ label.name }}
            </option>
          }
        </select>
      </div>
      <button
        type="submit"
        class="btn btn--primary quick__submit"
        [disabled]="!valid() || pending()"
      >
        {{ submitLabel() }}
      </button>
    </form>
    @if (error(); as message) {
      <p class="quick__error" role="alert">{{ message }}</p>
    }
  `,
  styles: `
    .quick {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: var(--space-3);

      .field {
        flex: 1 1 150px;
        margin: 0;
      }
    }

    .quick__amount {
      max-width: 160px;
    }

    .quick__submit {
      flex: 0 0 auto;
    }

    .quick__error {
      margin: var(--space-2) 0 0;
      color: var(--color-danger);
      font-size: var(--text-s);
    }

    @media (max-width: 600px) {
      .quick__amount {
        max-width: none;
      }

      .quick__submit {
        flex: 1 1 100%;
      }
    }
  `,
})
export class QuickEntry {
  private readonly api = inject(MonthsApi);

  readonly summary = input.required<MonthSummary>();
  /** Emitted with a short description once the entry is saved. */
  readonly added = output<string>();

  protected readonly outside = OUTSIDE;
  protected readonly amountText = signal('');
  private readonly chosenTarget = signal<string | null>(null);
  protected readonly fromId = signal<string>(OUTSIDE);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly labels = computed(() => this.summary().labels.filter((l) => !l.archived));
  protected readonly targetId = computed(() => {
    const chosen = this.chosenTarget();
    return (
      this.labels().find((l) => l.label_id === chosen)?.label_id ?? this.labels()[0]?.label_id ?? ''
    );
  });
  protected readonly sources = computed(() =>
    this.labels().filter((l) => l.label_id !== this.targetId()),
  );
  private readonly cents = computed(() => toCents(this.amountText()));
  protected readonly valid = computed(
    () =>
      !!this.targetId() &&
      (this.cents() ?? 0) > 0 &&
      (this.fromId() === OUTSIDE || this.sources().some((l) => l.label_id === this.fromId())),
  );
  protected readonly submitLabel = computed(() => {
    const cents = this.cents();
    const money = cents ? formatMoney(fromCents(cents)) : '';
    return `${this.fromId() === OUTSIDE ? 'Add' : 'Move'} ${money}`.trim();
  });

  protected setTarget(id: string): void {
    this.chosenTarget.set(id);
    if (this.fromId() === id) this.fromId.set(OUTSIDE);
  }

  protected submit(): void {
    if (this.pending() || !this.valid()) return;
    const summary = this.summary();
    const amount = fromCents(this.cents()!);
    const date = defaultDate(summary.year, summary.month);
    const name = (id: string) => this.labels().find((l) => l.label_id === id)?.name ?? '';
    const outside = this.fromId() === OUTSIDE;
    const request: Observable<unknown> = outside
      ? this.api.addMoney(summary.month_id, {
          label_id: this.targetId(),
          amount,
          occurred_on: date,
        })
      : this.api.transfer(summary.month_id, {
          from_label_id: this.fromId(),
          to_label_id: this.targetId(),
          amount,
          occurred_on: date,
        });
    const description = outside
      ? `${formatMoney(amount)} added to ${name(this.targetId())}`
      : `${formatMoney(amount)} moved from ${name(this.fromId())} to ${name(this.targetId())}`;
    this.pending.set(true);
    this.error.set(null);
    request.subscribe({
      next: () => {
        this.pending.set(false);
        this.amountText.set('');
        this.fromId.set(OUTSIDE);
        this.added.emit(description);
      },
      error: (error: unknown) => {
        this.pending.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
