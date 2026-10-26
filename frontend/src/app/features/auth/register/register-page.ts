import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
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
import { passwordPolicy } from '../../../shared/forms/password-policy';
import { authErrorKey } from '../auth-errors';

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

/** Sets `passwordMismatch` on the confirmation field when it differs. */
function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  const password = group.get('password');
  const confirm = group.get('confirmPassword');
  if (!password || !confirm) return null;
  const mismatch = confirm.value !== '' && password.value !== confirm.value;
  const errors = { ...(confirm.errors ?? {}) };
  if (mismatch) {
    errors['passwordMismatch'] = true;
  } else {
    delete errors['passwordMismatch'];
  }
  confirm.setErrors(Object.keys(errors).length ? errors : null);
  return null;
}

@Component({
  selector: 'app-register-page',
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
  templateUrl: './register-page.html',
  styleUrl: '../auth-form.scss',
})
export default class RegisterPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  readonly returnUrl = input<string>();

  protected readonly form = inject(NonNullableFormBuilder).group(
    {
      name: ['', [Validators.required, Validators.maxLength(100)]],
      email: ['', [Validators.required, Validators.email]],
      password: [
        '',
        [
          Validators.required,
          Validators.minLength(PASSWORD_MIN_LENGTH),
          Validators.maxLength(PASSWORD_MAX_LENGTH),
          passwordPolicy,
        ],
      ],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: passwordsMatch },
  );
  protected readonly pending = signal(false);
  protected readonly errorKey = signal<string | null>(null);
  protected readonly showPassword = signal(false);
  protected readonly fieldError = fieldError;

  protected submit(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { name, email, password } = this.form.getRawValue();
    this.pending.set(true);
    this.errorKey.set(null);
    this.auth
      .register({ name: name.trim(), email, password })
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => void this.router.navigateByUrl(safeReturnUrl(this.returnUrl())),
        error: (error: unknown) => this.errorKey.set(authErrorKey(error, 'register')),
      });
  }
}
