import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { apiErrorMessage } from '../../../core/api/api-errors';
import { AuthStore } from '../../../core/auth/auth-store';
import { safeReturnUrl } from '../../../core/auth/auth.guards';
import { Icon } from '../../../shared/ui/icon';

/**
 * Second sign-in step: the 6-digit code from the authenticator app, or a
 * recovery code. The ticket comes from the password step (kept in the store)
 * or from Google, in the URL fragment so it never reaches a server log.
 */
@Component({
  selector: 'app-two-factor-page',
  imports: [Icon, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stack">
      @if (!ticket()) {
        <div class="alert" role="alert">
          <app-icon name="alert" [size]="18" />
          <span>This sign-in expired. Please start again.</span>
        </div>
        <a class="btn btn--primary btn--block" routerLink="/auth/login">Sign in</a>
      } @else {
        @if (error(); as message) {
          <div class="alert" role="alert">
            <app-icon name="alert" [size]="18" />
            <span>{{ message }}</span>
          </div>
        }
        <form (submit)="$event.preventDefault(); submit()">
          <p class="note">
            {{
              recovery()
                ? 'Enter one of the recovery codes you saved. Each one works once.'
                : 'Open your authenticator app and enter the 6-digit code for FinnancialSystem.'
            }}
          </p>
          <div class="field">
            <label for="two-factor-code">{{ recovery() ? 'Recovery code' : 'Code' }}</label>
            <input
              id="two-factor-code"
              class="field__input code"
              [attr.inputmode]="recovery() ? 'text' : 'numeric'"
              [attr.autocomplete]="recovery() ? 'off' : 'one-time-code'"
              [attr.maxlength]="recovery() ? 20 : 6"
              [value]="code()"
              (input)="code.set($any($event.target).value)"
            />
          </div>
          <button
            class="btn btn--primary btn--block"
            type="submit"
            [disabled]="!valid() || pending()"
          >
            @if (pending()) {
              <span class="spinner" aria-hidden="true"></span>
              <span class="visually-hidden">Checking</span>
            } @else {
              Continue
            }
          </button>
          <p class="note">
            <button type="button" class="link-button" (click)="toggleRecovery()">
              {{
                recovery() ? 'Use the code from the app' : 'Lost your phone? Use a recovery code'
              }}
            </button>
          </p>
        </form>
      }
    </div>
  `,
  styleUrl: '../auth-form.scss',
  styles: `
    .code {
      font-family: var(--font-mono);
      font-size: var(--text-l);
      letter-spacing: 0.2em;
    }
  `,
})
export default class TwoFactorPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  readonly returnUrl = input<string>();

  protected readonly ticket = this.auth.pendingTicket;
  protected readonly code = signal('');
  protected readonly recovery = signal(false);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly valid = computed(() => {
    const value = this.code().replace(/\s/g, '');
    return this.recovery() ? value.length >= 10 : /^\d{6}$/.test(value);
  });

  constructor() {
    // From Google: /auth/two-factor#ticket=…; take it and clean the address bar.
    const fragment = new URLSearchParams(window.location.hash.slice(1)).get('ticket');
    if (fragment) {
      this.auth.pendingTicket.set(fragment);
      history.replaceState(history.state, '', window.location.pathname + window.location.search);
    }
  }

  protected toggleRecovery(): void {
    this.recovery.set(!this.recovery());
    this.code.set('');
    this.error.set(null);
  }

  protected submit(): void {
    if (!this.valid() || this.pending()) return;
    this.pending.set(true);
    this.error.set(null);
    this.auth
      .completeTwoFactor(this.code().trim())
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => void this.router.navigateByUrl(safeReturnUrl(this.returnUrl())),
        error: (error: unknown) => {
          this.code.set('');
          this.error.set(apiErrorMessage(error));
          // An expired ticket cannot be retried: start over.
          if (apiErrorMessage(error).startsWith('The sign-in expired')) {
            this.auth.pendingTicket.set(null);
          }
        },
      });
  }
}
