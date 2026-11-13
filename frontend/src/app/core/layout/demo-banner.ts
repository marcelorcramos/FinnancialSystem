import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { AuthStore } from '../auth/auth-store';
import { Icon } from '../../shared/ui/icon';

/** Tells a demo visitor that the data is temporary and how to keep going for real. */
@Component({
  selector: 'app-demo-banner',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (hoursLeft(); as hours) {
      <div class="banner" role="region" aria-label="Demo account">
        <app-icon name="info" [size]="18" />
        <p class="banner__text">
          You are exploring a demo with sample data. Change anything you like: it is deleted in
          {{ hours === 1 ? 'about an hour' : hours + ' hours' }}.
        </p>
        <button type="button" class="btn btn--primary" (click)="createAccount()">
          Create my own account
        </button>
      </div>
    }
  `,
  styles: `
    .banner {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2) var(--space-5);
      border-bottom: 1px solid var(--color-accent);
      background: var(--color-surface-raised);
      font-size: var(--text-s);
    }

    .banner__text {
      flex: 1 1 16rem;
      margin: 0;
    }
  `,
})
export class DemoBanner {
  private readonly auth = inject(AuthStore);

  protected readonly hoursLeft = computed(() => {
    const expires = this.auth.user()?.demo_expires_at;
    if (!expires) return null;
    return Math.max(1, Math.ceil((new Date(expires).getTime() - Date.now()) / 3_600_000));
  });

  /** Leaves the demo (it is deleted later anyway) for the sign-up page. */
  protected createAccount(): void {
    this.auth.logout('/auth/register').subscribe();
  }
}
