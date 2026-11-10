import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { finalize } from 'rxjs';

import { AuthApi } from '../../../core/auth/auth-api';
import { AuthStore } from '../../../core/auth/auth-store';
import { apiErrorMessage } from '../../../core/api/api-errors';
import { visibleError } from '../../../shared/forms/field-error';
import { passwordPolicy, passwordRules } from '../../../shared/forms/password-policy';
import { Icon } from '../../../shared/ui/icon';
import { ToastService } from '../../../shared/ui/toast.service';
import { PASSWORD_MAX_LENGTH } from '../register/register-page';

/** Chooses a new password with the token from the emailed link. */
@Component({
  selector: 'app-reset-password-page',
  imports: [Icon, ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stack">
      @if (!token() || expired()) {
        <div class="alert" role="alert">
          <app-icon name="alert" [size]="18" />
          <span>This link is invalid or has expired. Ask for a new one.</span>
        </div>
        <a class="btn btn--primary btn--block" routerLink="/auth/forgot-password"
          >Send a new link</a
        >
      } @else {
        @if (error(); as message) {
          <div class="alert" role="alert">
            <app-icon name="alert" [size]="18" />
            <span>{{ message }}</span>
          </div>
        }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <p class="note">Choose a new password. You will be signed out on every device.</p>
          <div class="field">
            <label for="reset-password">New password</label>
            @let passwordError = visibleError(form.controls.password);
            <div class="field__control">
              <input
                id="reset-password"
                class="field__input field__input--with-action"
                [type]="showPassword() ? 'text' : 'password'"
                formControlName="password"
                autocomplete="new-password"
                aria-describedby="reset-password-rules"
                [attr.aria-invalid]="!!passwordError"
              />
              <button
                type="button"
                class="btn btn--icon btn--quiet field__action"
                [attr.aria-label]="showPassword() ? 'Hide password' : 'Show password'"
                [attr.aria-pressed]="showPassword()"
                (click)="showPassword.set(!showPassword())"
              >
                <app-icon [name]="showPassword() ? 'eye-off' : 'eye'" />
              </button>
            </div>
            @if (passwordError) {
              <span class="field__error">{{ passwordError }}</span>
            }
          </div>
          <ul id="reset-password-rules" class="rules" aria-label="Password rules">
            @for (rule of rules(); track rule.label) {
              <li class="rule" [class.rule--met]="rule.met">
                <app-icon [name]="rule.met ? 'check' : 'close'" [size]="14" />
                <span>{{ rule.label }}</span>
                <span class="visually-hidden">{{ rule.met ? '(done)' : '(missing)' }}</span>
              </li>
            }
          </ul>
          <button class="btn btn--primary btn--block" type="submit" [disabled]="pending()">
            @if (pending()) {
              <span class="spinner" aria-hidden="true"></span>
              <span class="visually-hidden">Saving</span>
            } @else {
              Save new password
            }
          </button>
        </form>
      }
    </div>
  `,
  styleUrl: '../auth-form.scss',
})
export default class ResetPasswordPage {
  private readonly api = inject(AuthApi);
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly toasts = inject(ToastService);

  /** From the link's query string (withComponentInputBinding). */
  readonly token = input<string>();

  protected readonly form = inject(NonNullableFormBuilder).group({
    password: [
      '',
      [Validators.required, Validators.maxLength(PASSWORD_MAX_LENGTH), passwordPolicy],
    ],
  });
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly expired = signal(false);
  protected readonly showPassword = signal(false);
  protected readonly visibleError = visibleError;

  private readonly password = toSignal(this.form.controls.password.valueChanges, {
    initialValue: '',
  });
  protected readonly rules = computed(() => passwordRules(this.password()));

  protected submit(): void {
    const token = this.token();
    if (this.pending() || !token) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    this.api
      .resetPassword(token, this.form.controls.password.value)
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => {
          // Every session ended on the API; this tab's too.
          this.auth.expireSession();
          this.toasts.show('Password changed. Sign in with the new one.');
          void this.router.navigateByUrl('/auth/login');
        },
        error: (error: unknown) => {
          if (error instanceof HttpErrorResponse && error.error?.code === 'invalid_token') {
            this.expired.set(true);
          } else {
            this.error.set(apiErrorMessage(error));
          }
        },
      });
  }
}
