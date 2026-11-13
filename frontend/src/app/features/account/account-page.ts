import { Dialog } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-errors';
import { AuthStore } from '../../core/auth/auth-store';
import { exportErrorMessage, ExportsService } from '../../core/exports/exports.service';
import { dialogA11y } from '../../shared/ui/dialog-a11y';
import { passwordRules } from '../../shared/forms/password-policy';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { DeleteAccountDialog } from './delete-account-dialog';
import { TwoFactorApi } from './two-factor-api';
import { TwoFactorDialog, TwoFactorMode } from './two-factor-dialog';
import { AuthApi } from '../../core/auth/auth-api';
import { TwoFactorStatus } from '../../core/api/types';

/** Every IANA time zone the browser knows, with the user's own first if it is missing. */
function timeZones(current: string): string[] {
  const all =
    typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [];
  return all.includes(current) ? all : [current, ...all];
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (
    (parts[0]?.[0] ?? '') + (parts.length > 1 ? (parts.at(-1)?.[0] ?? '') : '')
  ).toUpperCase();
}

/** Profile, password, sessions and data of the signed-in user. */
@Component({
  selector: 'app-account-page',
  imports: [Icon, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './account-page.html',
  styleUrl: './account-page.scss',
})
export default class AccountPage {
  private readonly auth = inject(AuthStore);
  private readonly toasts = inject(ToastService);
  private readonly exports = inject(ExportsService);
  private readonly dialog = inject(Dialog);
  private readonly twoFactorApi = inject(TwoFactorApi);
  private readonly authApi = inject(AuthApi);

  protected readonly user = this.auth.user;
  protected readonly isDemo = computed(() => !!this.user()?.demo_expires_at);
  protected readonly initials = computed(() => initials(this.user()?.name ?? ''));

  // Profile
  protected readonly name = signal(this.user()?.name ?? '');
  protected readonly timezone = signal(this.user()?.timezone ?? 'Europe/Lisbon');
  protected readonly zones = timeZones(this.timezone());
  protected readonly autoNewMonth = signal(this.user()?.auto_new_month ?? false);
  protected readonly profileChanged = computed(() => {
    const user = this.user();
    return (
      !!user &&
      (this.name().trim() !== user.name ||
        this.timezone() !== user.timezone ||
        this.autoNewMonth() !== user.auto_new_month)
    );
  });
  protected readonly profileValid = computed(() => this.name().trim().length > 0);
  protected readonly savingProfile = signal(false);
  protected readonly profileError = signal<string | null>(null);

  // Password
  protected readonly currentPassword = signal('');
  protected readonly newPassword = signal('');
  protected readonly rules = computed(() => passwordRules(this.newPassword()));
  protected readonly passwordValid = computed(
    () => this.currentPassword().length > 0 && this.rules().every((rule) => rule.met),
  );
  protected readonly changingPassword = signal(false);
  protected readonly passwordError = signal<string | null>(null);

  // Sessions
  protected readonly signingOut = signal(false);

  // Two-factor sign-in and the Google-only password link
  protected readonly twoFactor = signal<TwoFactorStatus | null>(null);
  protected readonly sendingPasswordLink = signal(false);

  // Email and data
  protected readonly resending = signal(false);
  protected readonly exporting = this.exports.busy;

  protected saveProfile(): void {
    if (!this.profileChanged() || !this.profileValid() || this.savingProfile()) return;
    this.savingProfile.set(true);
    this.profileError.set(null);
    const changes = {
      name: this.name().trim(),
      timezone: this.timezone(),
      auto_new_month: this.autoNewMonth(),
    };
    this.auth.updateProfile(changes).subscribe({
      next: (user) => {
        this.savingProfile.set(false);
        this.name.set(user.name);
        this.toasts.show('Profile saved');
      },
      error: (error: unknown) => {
        this.savingProfile.set(false);
        this.profileError.set(apiErrorMessage(error));
      },
    });
  }

  protected changePassword(): void {
    if (!this.passwordValid() || this.changingPassword()) return;
    this.changingPassword.set(true);
    this.passwordError.set(null);
    this.auth.changePassword(this.currentPassword(), this.newPassword()).subscribe({
      next: () => {
        this.changingPassword.set(false);
        this.currentPassword.set('');
        this.newPassword.set('');
        this.toasts.show('Password updated. Other devices were signed out.');
      },
      error: (error: unknown) => {
        this.changingPassword.set(false);
        this.passwordError.set(apiErrorMessage(error));
      },
    });
  }

  protected signOutOthers(): void {
    if (this.signingOut()) return;
    this.signingOut.set(true);
    this.auth.logoutOthers().subscribe({
      next: () => {
        this.signingOut.set(false);
        this.toasts.show('Other devices were signed out');
      },
      error: (error: unknown) => {
        this.signingOut.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }

  constructor() {
    this.loadTwoFactor();
  }

  private loadTwoFactor(): void {
    this.twoFactorApi.status().subscribe({
      next: (status) => this.twoFactor.set(status),
      error: () => this.twoFactor.set(null),
    });
  }

  protected openTwoFactor(mode: TwoFactorMode): void {
    this.dialog
      .open<boolean, TwoFactorMode>(TwoFactorDialog, {
        data: mode,
        ...dialogA11y('two-factor-dialog-title'),
      })
      .closed.subscribe((changed) => {
        if (!changed) return;
        this.loadTwoFactor();
        this.auth.reloadUser().subscribe();
        if (mode === 'turn-on') this.toasts.show('Two-factor sign-in is on');
        if (mode === 'turn-off') this.toasts.show('Two-factor sign-in is off');
      });
  }

  /** Google-only accounts add a password through the reset email, which proves the address. */
  protected sendPasswordLink(): void {
    const email = this.user()?.email;
    if (!email) return;
    this.sendingPasswordLink.set(true);
    this.authApi.requestPasswordReset(email).subscribe({
      next: () => {
        this.sendingPasswordLink.set(false);
        this.toasts.show(`We sent a link to ${email}`);
      },
      error: (error: unknown) => {
        this.sendingPasswordLink.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }

  protected resendVerification(): void {
    this.resending.set(true);
    this.auth.resendVerification().subscribe({
      next: () => {
        this.resending.set(false);
        this.toasts.show(`A new link is on its way to ${this.user()?.email}`);
      },
      error: (error: unknown) => {
        this.resending.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }

  protected downloadData(): void {
    this.toasts.show('Preparing your data…');
    this.exports.account().subscribe({
      next: (done) => this.toasts.show(`${done.filename} downloaded`),
      error: (error: unknown) => this.toasts.show(exportErrorMessage(error)),
    });
  }

  protected deleteAccount(): void {
    this.dialog
      .open<boolean>(DeleteAccountDialog, {
        ...dialogA11y('delete-account-title', { alert: true, describedBy: 'delete-account-text' }),
      })
      .closed.subscribe((deleted) => {
        if (deleted) this.toasts.show('Your account was deleted');
      });
  }
}
