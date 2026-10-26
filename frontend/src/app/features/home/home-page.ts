import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { TranslocoPipe } from '@jsverse/transloco';

import { AuthStore } from '../../core/auth/auth-store';

@Component({
  selector: 'app-home-page',
  imports: [MatIconModule, TranslocoPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>{{ 'home.greeting' | transloco: { name: auth.user()?.name ?? '' } }}</h1>
    <section class="empty">
      <mat-icon aria-hidden="true">calendar_month</mat-icon>
      <p>{{ 'home.intro' | transloco }}</p>
    </section>
  `,
  styles: `
    h1 {
      margin: 0 0 var(--space-5);
      font: var(--mat-sys-headline-small);
    }

    .empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-7) var(--space-4);
      border: 1px dashed var(--mat-sys-outline-variant);
      border-radius: var(--radius-l);
      color: var(--mat-sys-on-surface-variant);
      text-align: center;

      mat-icon {
        width: 40px;
        height: 40px;
        font-size: 40px;
      }

      p {
        margin: 0;
      }
    }
  `,
})
export default class HomePage {
  protected readonly auth = inject(AuthStore);
}
