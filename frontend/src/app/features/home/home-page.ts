import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { AuthStore } from '../../core/auth/auth-store';
import { Icon } from '../../shared/ui/icon';

@Component({
  selector: 'app-home-page',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>Hello, {{ auth.user()?.name }}</h1>
    <section class="empty panel">
      <app-icon name="month" [size]="40" />
      <p>Your month, labels and charts will show up here.</p>
    </section>
  `,
  styles: `
    h1 {
      margin: var(--space-4) 0 var(--space-5);
      font-size: var(--text-2xl);
      letter-spacing: -0.02em;
    }

    .empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-7) var(--space-4);
      border-style: dashed;
      color: var(--color-text-muted);
      text-align: center;

      p {
        margin: 0;
      }
    }
  `,
})
export default class HomePage {
  protected readonly auth = inject(AuthStore);
}
