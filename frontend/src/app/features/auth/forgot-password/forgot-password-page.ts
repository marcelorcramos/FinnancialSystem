import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthApi } from '../../../core/auth/auth-api';
import { apiErrorMessage } from '../../../core/api/api-errors';
import { visibleError } from '../../../shared/forms/field-error';
import { Icon } from '../../../shared/ui/icon';

/** Asks for a reset link. The answer never says whether the email has an account. */
@Component({
  selector: 'app-forgot-password-page',
  imports: [Icon, ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="stack">
      @if (sentTo(); as email) {
        <div class="alert alert--info" role="status">
          <app-icon name="info" [size]="18" />
          <span
            >If {{ email }} has an account, a link to choose a new password is on its way. It works
            for 1 hour.</span
          >
        </div>
        <p class="note">
          No email? Check the spam folder, or
          <button type="button" class="link-button" (click)="sentTo.set(null)">try again</button>.
        </p>
        <a class="btn btn--block" routerLink="/auth/login">Back to sign in</a>
      } @else {
        @if (error(); as message) {
          <div class="alert" role="alert">
            <app-icon name="alert" [size]="18" />
            <span>{{ message }}</span>
          </div>
        }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <p class="note">Enter your account's email and we will send you a link to reset it.</p>
          <div class="field">
            <label for="forgot-email">Email</label>
            @let emailError = visibleError(form.controls.email);
            <input
              id="forgot-email"
              class="field__input"
              type="email"
              formControlName="email"
              autocomplete="email"
              inputmode="email"
              [attr.aria-invalid]="!!emailError"
              [attr.aria-describedby]="emailError ? 'forgot-email-error' : null"
            />
            @if (emailError) {
              <span id="forgot-email-error" class="field__error">{{ emailError }}</span>
            }
          </div>
          <button class="btn btn--primary btn--block" type="submit" [disabled]="pending()">
            @if (pending()) {
              <span class="spinner" aria-hidden="true"></span>
              <span class="visually-hidden">Sending</span>
            } @else {
              Send reset link
            }
          </button>
          <p class="note"><a routerLink="/auth/login">Back to sign in</a></p>
        </form>
      }
    </div>
  `,
  styleUrl: '../auth-form.scss',
})
export default class ForgotPasswordPage {
  private readonly api = inject(AuthApi);

  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
  });
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly sentTo = signal<string | null>(null);
  protected readonly visibleError = visibleError;

  protected submit(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const email = this.form.controls.email.value.trim();
    this.pending.set(true);
    this.error.set(null);
    this.api
      .requestPasswordReset(email)
      .pipe(finalize(() => this.pending.set(false)))
      .subscribe({
        next: () => this.sentTo.set(email),
        error: (error: unknown) => this.error.set(apiErrorMessage(error)),
      });
  }
}
