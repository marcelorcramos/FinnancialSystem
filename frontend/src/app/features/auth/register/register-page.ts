import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { safeReturnUrl } from '../../../core/auth/auth.guards';
import { visibleError } from '../../../shared/forms/field-error';
import { passwordPolicy, passwordRules } from '../../../shared/forms/password-policy';
import { Icon } from '../../../shared/ui/icon';
import { authErrorMessage } from '../auth-errors';

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
  imports: [Icon, ReactiveFormsModule],
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
        [Validators.required, Validators.maxLength(PASSWORD_MAX_LENGTH), passwordPolicy],
      ],
      confirmPassword: ['', [Validators.required]],
    },
    { validators: passwordsMatch },
  );
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly showPassword = signal(false);
  protected readonly visibleError = visibleError;

  private readonly password = toSignal(this.form.controls.password.valueChanges, {
    initialValue: '',
  });
  protected readonly rules = computed(() => passwordRules(this.password()));

  protected submit(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { name, email, password } = this.form.getRawValue();
    this.pending.set(true);
    this.error.set(null);
    this.auth
      .register({ name: name.trim(), email, password })
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => void this.router.navigateByUrl(safeReturnUrl(this.returnUrl())),
        error: (error: unknown) => this.error.set(authErrorMessage(error, 'register')),
      });
  }
}
