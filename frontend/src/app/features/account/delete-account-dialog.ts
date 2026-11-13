import { DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { apiErrorMessage } from '../../core/api/api-errors';
import { AuthStore } from '../../core/auth/auth-store';
import { Icon } from '../../shared/ui/icon';

/**
 * Confirms deleting the account for good: the password (or, for accounts without
 * one, the typed email) and an explicit "I understand".
 */
@Component({
  selector: 'app-delete-account-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="dialog" (submit)="$event.preventDefault(); confirm()">
      <header class="head">
        <h2 id="delete-account-title">Delete your account?</h2>
        <button
          type="button"
          class="btn btn--icon btn--quiet"
          aria-label="Close"
          (click)="ref.close()"
        >
          <app-icon name="close" />
        </button>
      </header>
      <p id="delete-account-text">
        Every month, entry, label, goal and receipt goes now, for good. There is no Undo. If you
        want a copy, download your data first.
      </p>
      @if (error(); as message) {
        <div class="alert" role="alert">
          <app-icon name="alert" [size]="18" />
          <span>{{ message }}</span>
        </div>
      }
      @if (hasPassword()) {
        <div class="field">
          <label for="delete-password">Password</label>
          <input
            id="delete-password"
            class="field__input"
            type="password"
            autocomplete="current-password"
            [value]="password()"
            (input)="password.set($any($event.target).value)"
          />
        </div>
      } @else {
        <div class="field">
          <label for="delete-email">Type your email ({{ email() }}) to confirm</label>
          <input
            id="delete-email"
            class="field__input"
            type="email"
            autocomplete="off"
            [value]="password()"
            (input)="password.set($any($event.target).value)"
          />
        </div>
      }
      <label class="check">
        <input
          type="checkbox"
          [checked]="understood()"
          (change)="understood.set($any($event.target).checked)"
        />
        I understand this cannot be undone
      </label>
      <div class="actions">
        <button type="button" class="btn btn--quiet" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn--danger" [disabled]="!ready() || pending()">
          {{ pending() ? 'Deleting…' : 'Delete account' }}
        </button>
      </div>
    </form>
  `,
  styleUrl: '../month/add-money-dialog.scss',
  styles: `
    .dialog {
      width: min(480px, calc(100vw - 32px));
    }

    p {
      margin: 0;
    }

    .check {
      display: flex;
      align-items: center;
      gap: var(--space-2);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: var(--space-2);
    }
  `,
})
export class DeleteAccountDialog {
  private readonly auth = inject(AuthStore);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);

  protected readonly hasPassword = computed(() => this.auth.user()?.has_password ?? true);
  protected readonly email = computed(() => this.auth.user()?.email ?? '');
  /** The password, or the typed email for accounts without a password. */
  protected readonly password = signal('');
  protected readonly understood = signal(false);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly ready = computed(() => this.password().length > 0 && this.understood());

  protected confirm(): void {
    if (!this.ready() || this.pending()) return;
    this.pending.set(true);
    this.error.set(null);
    const confirmation = this.hasPassword()
      ? { password: this.password() }
      : { confirm_email: this.password() };
    this.auth.deleteAccount(confirmation).subscribe({
      next: () => this.ref.close(true),
      error: (error: unknown) => {
        this.pending.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
