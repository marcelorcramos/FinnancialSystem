import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterLink } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';
import { finalize } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { safeReturnUrl } from '../../../core/auth/auth.guards';
import { fieldError } from '../../../shared/forms/field-error';
import { authErrorKey } from '../auth-errors';

@Component({
  selector: 'app-login-page',
  imports: [
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    RouterLink,
    TranslocoPipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './login-page.html',
  styleUrl: '../auth-form.scss',
})
export default class LoginPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  /** Bound from the query string (withComponentInputBinding). */
  readonly returnUrl = input<string>();

  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });
  protected readonly pending = signal(false);
  protected readonly errorKey = signal<string | null>(null);
  protected readonly showPassword = signal(false);
  protected readonly sessionExpired = this.auth.sessionExpired;
  protected readonly fieldError = fieldError;

  protected submit(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.pending.set(true);
    this.errorKey.set(null);
    this.auth
      .login(this.form.getRawValue())
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => void this.router.navigateByUrl(safeReturnUrl(this.returnUrl())),
        error: (error: unknown) => this.errorKey.set(authErrorKey(error, 'login')),
      });
  }
}
