import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Icon } from '../ui/icon';
import { DEFAULT_CURRENCY, DEFAULT_MONEY_LOCALE, formatMoney, MoneyValue } from './format-money';
import { Kind, KIND_ICONS, KIND_NAMES } from './kind';

/**
 * A monetary value coloured by its kind. Colour is never the only signal:
 * it always comes with the kind icon and the kind name (visible, or only for
 * screen readers when `showKind` is false).
 */
@Component({
  selector: 'app-money-amount',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'money-amount',
    '[attr.data-kind]': 'kind()',
  },
  template: `
    <app-icon class="money-amount__icon" [name]="icon()" [size]="16" />
    <span class="money-amount__value">{{ formatted() }}</span>
    <span class="money-amount__kind" [class.visually-hidden]="!showKind()">{{ kindName() }}</span>
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
  protected readonly kindName = computed(() => KIND_NAMES[this.kind()]);
  protected readonly formatted = computed(() =>
    formatMoney(this.amount(), this.currency(), this.locale()),
  );
}
