import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { RecoveryCodes, TwoFactorSetup } from '../../core/api/types';
import { Icon } from '../../shared/ui/icon';
import { TwoFactorApi } from './two-factor-api';

/** turn-on: scan, confirm, save codes · turn-off: confirm · new-codes: confirm, save codes. */
export type TwoFactorMode = 'turn-on' | 'turn-off' | 'new-codes';

const TITLES: Record<TwoFactorMode, string> = {
  'turn-on': 'Turn on two-factor sign-in',
  'turn-off': 'Turn off two-factor sign-in',
  'new-codes': 'New recovery codes',
};

/** Closes with true when something changed. */
@Component({
  selector: 'app-two-factor-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="dialog">
      <header class="head">
        <h2 id="two-factor-dialog-title">{{ title }}</h2>
        <button
          type="button"
          class="btn btn--icon btn--quiet"
          aria-label="Close"
          (click)="ref.close(changed())"
        >
          <app-icon name="close" />
        </button>
      </header>

      @if (error(); as message) {
        <div class="alert" role="alert">
          <app-icon name="alert" [size]="18" />
          <span>{{ message }}</span>
        </div>
      }

      @if (codes(); as list) {
        <p>
          Save these recovery codes somewhere safe, like a password manager. Each one signs you in
          once if you lose your phone. They will not be shown again.
        </p>
        <ol class="codes" aria-label="Recovery codes">
          @for (code of list; track code) {
            <li class="num">{{ code }}</li>
          }
        </ol>
        <div class="actions">
          <button type="button" class="btn" (click)="copy(list)">
            {{ copied() ? 'Copied' : 'Copy codes' }}
          </button>
          <button type="button" class="btn btn--primary" (click)="ref.close(true)">
            I saved them
          </button>
        </div>
      } @else {
        @if (mode === 'turn-on') {
          @if (setup(); as info) {
            <ol class="steps">
              <li>
                Scan this code with an authenticator app (Google Authenticator, 1Password, Authy…).
                <img
                  class="qr"
                  [src]="info.qr_code"
                  alt="QR code to add FinnancialSystem to your authenticator app"
                />
                <details>
                  <summary>Can't scan it?</summary>
                  <p>
                    Type this key in the app instead: <code class="num">{{ info.secret }}</code>
                  </p>
                </details>
              </li>
              <li>Enter the 6-digit code the app shows.</li>
            </ol>
          } @else if (!error()) {
            <p class="muted" role="status">Preparing…</p>
          }
        } @else {
          <p>Enter the 6-digit code from your authenticator app, or one of your recovery codes.</p>
        }
        @if (mode !== 'turn-on' || setup()) {
          <form class="confirm" (submit)="$event.preventDefault(); confirm()">
            <div class="field">
              <label for="two-factor-dialog-code">Code</label>
              <input
                id="two-factor-dialog-code"
                class="field__input num"
                autocomplete="one-time-code"
                [attr.inputmode]="mode === 'turn-on' ? 'numeric' : 'text'"
                maxlength="20"
                [value]="code()"
                (input)="code.set($any($event.target).value)"
              />
            </div>
            <button
              type="submit"
              class="btn"
              [class.btn--primary]="mode !== 'turn-off'"
              [class.btn--danger]="mode === 'turn-off'"
              [disabled]="!valid() || pending()"
            >
              {{ action }}
            </button>
          </form>
        }
      }
    </section>
  `,
  styleUrl: '../month/add-money-dialog.scss',
  styles: `
    .dialog {
      width: min(520px, calc(100vw - 32px));
    }

    p {
      margin: 0;
    }

    .steps {
      display: flex;
      flex-direction: column;
      gap: var(--space-4);
      margin: 0;
      padding-left: var(--space-5);
    }

    .qr {
      display: block;
      width: 180px;
      height: 180px;
      margin: var(--space-3) 0;
      border-radius: var(--radius-s);
      background: #fff;
    }

    code {
      overflow-wrap: anywhere;
    }

    .codes {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
      gap: var(--space-2) var(--space-4);
      margin: 0;
      padding: var(--space-4) var(--space-4) var(--space-4) var(--space-6);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-m);
    }

    .confirm,
    .actions {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      gap: var(--space-3);
    }

    .actions {
      justify-content: flex-end;
    }
  `,
})
export class TwoFactorDialog {
  private readonly api = inject(TwoFactorApi);
  protected readonly ref = inject<DialogRef<boolean>>(DialogRef);
  protected readonly mode = inject<TwoFactorMode>(DIALOG_DATA);

  protected readonly title = TITLES[this.mode];
  protected readonly action =
    this.mode === 'turn-on' ? 'Turn on' : this.mode === 'turn-off' ? 'Turn off' : 'Show new codes';
  protected readonly setup = signal<TwoFactorSetup | null>(null);
  protected readonly codes = signal<string[] | null>(null);
  protected readonly code = signal('');
  protected readonly pending = signal(false);
  protected readonly copied = signal(false);
  protected readonly changed = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly valid = computed(() => this.code().trim().length >= 6);

  constructor() {
    if (this.mode === 'turn-on') {
      this.api.setup().subscribe({
        next: (info) => this.setup.set(info),
        error: (error: unknown) => this.error.set(apiErrorMessage(error)),
      });
    }
  }

  protected confirm(): void {
    if (!this.valid() || this.pending()) return;
    const code = this.code().trim();
    if (this.mode === 'turn-off') {
      this.run(this.api.disable(code), () => this.ref.close(true));
    } else {
      const request =
        this.mode === 'turn-on' ? this.api.enable(code) : this.api.recoveryCodes(code);
      this.run(request, (result) => {
        this.changed.set(true);
        this.codes.set((result as RecoveryCodes).codes);
      });
    }
  }

  protected copy(codes: string[]): void {
    void navigator.clipboard?.writeText(codes.join('\n')).then(() => this.copied.set(true));
  }

  private run<T>(request: Observable<T>, done: (result: T) => void): void {
    this.pending.set(true);
    this.error.set(null);
    request.subscribe({
      next: (result) => {
        this.pending.set(false);
        done(result);
      },
      error: (error: unknown) => {
        this.pending.set(false);
        this.code.set('');
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
