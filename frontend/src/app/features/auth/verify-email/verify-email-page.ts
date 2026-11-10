import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  signal,
  untracked,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { apiErrorMessage } from '../../../core/api/api-errors';
import { Icon } from '../../../shared/ui/icon';
import { ToastService } from '../../../shared/ui/toast.service';

type State = 'checking' | 'confirmed' | 'invalid';

/** Confirms the email with the token from the emailed link, as soon as it opens. */
@Component({
  selector: 'app-verify-email-page',
  imports: [Icon, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stack">
      @switch (state()) {
        @case ('checking') {
          <p class="status" role="status">
            <span class="spinner" aria-hidden="true"></span> Confirming your email…
          </p>
        }
        @case ('confirmed') {
          <div class="alert alert--success" role="status">
            <app-icon name="check" [size]="18" />
            <span>Your email is confirmed. Thank you!</span>
          </div>
          <a class="btn btn--primary btn--block" [routerLink]="signedIn() ? '/' : '/auth/login'">
            {{ signedIn() ? 'Continue' : 'Sign in' }}
          </a>
        }
        @case ('invalid') {
          <div class="alert" role="alert">
            <app-icon name="alert" [size]="18" />
            <span>{{ message() }}</span>
          </div>
          @if (signedIn()) {
            <button
              type="button"
              class="btn btn--primary btn--block"
              [disabled]="resending()"
              (click)="resend()"
            >
              Send a new link
            </button>
          } @else {
            <p class="note">Sign in to ask for a new link.</p>
            <a class="btn btn--block" routerLink="/auth/login">Sign in</a>
          }
        }
      }
    </div>
  `,
  styleUrl: '../auth-form.scss',
  styles: `
    .status {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      margin: 0;
    }
  `,
})
export default class VerifyEmailPage {
  private readonly auth = inject(AuthStore);
  private readonly toasts = inject(ToastService);

  readonly token = input<string>();

  protected readonly state = signal<State>('checking');
  protected readonly message = signal('');
  protected readonly resending = signal(false);
  protected readonly signedIn = this.auth.isAuthenticated;

  constructor() {
    effect(() => {
      const token = this.token();
      untracked(() => this.confirm(token));
    });
  }

  private confirm(token: string | undefined): void {
    if (!token) {
      this.fail('This link is invalid or has expired. Ask for a new one.');
      return;
    }
    this.state.set('checking');
    // Resume a session first (this page has no guard), so a signed-in user sees it confirmed.
    this.auth
      .restoreSession()
      .pipe(switchMap(() => this.auth.verifyEmail(token)))
      .subscribe({
        next: () => this.state.set('confirmed'),
        error: (error: unknown) => this.fail(apiErrorMessage(error)),
      });
  }

  private fail(message: string): void {
    this.message.set(message);
    this.state.set('invalid');
  }

  protected resend(): void {
    this.resending.set(true);
    this.auth.resendVerification().subscribe({
      next: () => {
        this.resending.set(false);
        this.toasts.show('A new link is on its way');
      },
      error: (error: unknown) => {
        this.resending.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }
}
