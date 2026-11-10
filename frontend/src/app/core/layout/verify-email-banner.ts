import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { apiErrorMessage } from '../api/api-errors';
import { AuthStore } from '../auth/auth-store';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';

/** Reminds a signed-in user to confirm their email, with a way to get a new link. */
@Component({
  selector: 'app-verify-email-banner',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (visible()) {
      <div class="banner" role="region" aria-label="Confirm your email">
        <app-icon name="info" [size]="18" />
        <p class="banner__text">
          Confirm your email: we sent a link to <strong>{{ email() }}</strong
          >.
        </p>
        <button
          type="button"
          class="btn banner__action"
          [disabled]="sending() || sent()"
          (click)="resend()"
        >
          {{ sent() ? 'Link sent' : 'Resend link' }}
        </button>
        <button
          type="button"
          class="btn btn--icon btn--quiet"
          aria-label="Hide this reminder"
          (click)="dismissed.set(true)"
        >
          <app-icon name="close" [size]="18" />
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
      border-bottom: 1px solid var(--color-border);
      background: var(--color-surface-raised);
      font-size: var(--text-s);
    }

    .banner__text {
      flex: 1 1 16rem;
      margin: 0;
      overflow-wrap: anywhere;
    }
  `,
})
export class VerifyEmailBanner {
  private readonly auth = inject(AuthStore);
  private readonly toasts = inject(ToastService);

  /** Hidden until the next page load. */
  protected readonly dismissed = signal(false);
  protected readonly sending = signal(false);
  protected readonly sent = signal(false);
  protected readonly email = computed(() => this.auth.user()?.email ?? '');
  protected readonly visible = computed(() => {
    const user = this.auth.user();
    return !!user && !user.email_verified_at && !this.dismissed();
  });

  protected resend(): void {
    this.sending.set(true);
    this.auth.resendVerification().subscribe({
      next: () => {
        this.sending.set(false);
        this.sent.set(true);
        this.toasts.show('A new link is on its way');
      },
      error: (error: unknown) => {
        this.sending.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }
}
