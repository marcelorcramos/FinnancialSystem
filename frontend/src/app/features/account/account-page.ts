import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-errors';
import { AuthStore } from '../../core/auth/auth-store';
import { passwordRules } from '../../shared/forms/password-policy';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';

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

/** Profile, password and sessions of the signed-in user. */
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

  protected readonly user = this.auth.user;
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
}
