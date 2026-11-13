import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { catchError, finalize, map, of } from 'rxjs';

import { AuthApi } from '../../../core/auth/auth-api';
import { AuthStore, TWO_FACTOR_PATH } from '../../../core/auth/auth-store';
import { safeReturnUrl } from '../../../core/auth/auth.guards';
import { visibleError } from '../../../shared/forms/field-error';
import { Icon } from '../../../shared/ui/icon';
import { authErrorMessage } from '../auth-errors';

@Component({
  selector: 'app-login-page',
  imports: [Icon, ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './login-page.html',
  styleUrl: '../auth-form.scss',
})
export default class LoginPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  /** Bound from the query string (withComponentInputBinding). */
  readonly returnUrl = input<string>();
  /** `google` after a failed Google sign-in. */
  readonly error = input<string>();

  /** The Google button shows only when the server has Google set up. */
  protected readonly google = toSignal(
    inject(AuthApi)
      .providers()
      .pipe(
        map((providers) => providers.google),
        catchError(() => of(false)),
      ),
    { initialValue: false },
  );
  protected readonly googleUrl = '/api/v1/auth/google/login';

  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });
  protected readonly pending = signal(false);
  protected readonly formError = signal<string | null>(null);
  protected readonly message = computed(
    () =>
      this.formError() ??
      (this.error() === 'google' ? 'Signing in with Google did not work. Please try again.' : null),
  );
  protected readonly showPassword = signal(false);
  protected readonly sessionExpired = this.auth.sessionExpired;
  protected readonly visibleError = visibleError;

  protected submit(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.pending.set(true);
    this.formError.set(null);
    this.auth
      .login(this.form.getRawValue())
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: (result) => {
          const returnUrl = safeReturnUrl(this.returnUrl());
          if ('ticket' in result) {
            void this.router.navigate([TWO_FACTOR_PATH], {
              queryParams: returnUrl === '/' ? {} : { returnUrl },
            });
          } else {
            void this.router.navigateByUrl(returnUrl);
          }
        },
        error: (error: unknown) => this.formError.set(authErrorMessage(error, 'login')),
      });
  }
}
