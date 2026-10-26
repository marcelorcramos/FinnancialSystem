import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoPipe } from '@jsverse/transloco';

import {
  DEFAULT_CURRENCY,
  DEFAULT_MONEY_LOCALE,
  formatMoney,
  MoneyValue,
} from './format-money';
import { Kind, KIND_ICONS } from './kind';

/**
 * A monetary value coloured by its kind. Colour is never the only signal:
 * it always comes with the kind icon and the kind name (visible, or only for
 * screen readers when `showKind` is false).
 */
@Component({
  selector: 'app-money-amount',
  imports: [MatIconModule, TranslocoPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'money-amount',
    '[attr.data-kind]': 'kind()',
  },
  template: `
    <mat-icon class="money-amount__icon" aria-hidden="true">{{ icon() }}</mat-icon>
    <span class="money-amount__value">{{ formatted() }}</span>
    <span class="money-amount__kind" [class.cdk-visually-hidden]="!showKind()">
      {{ 'kind.' + kind() | transloco }}
    </span>
  `,
  styleUrl: './money-amount.scss',
})
export class MoneyAmount {
  readonly amount = input.required<MoneyValue>();
  readonly kind = input.required<Kind>();
  readonly currency = input(DEFAULT_CURRENCY);
  readonly locale = input(DEFAULT_MONEY_LOCALE);
  readonly showKind = input(true);

  protected readonly icon = computed(() => KIND_ICONS[this.kind()]);
  protected readonly formatted = computed(() =>
    formatMoney(this.amount(), this.currency(), this.locale()),
  );
}
