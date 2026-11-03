import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../core/auth/auth-store';
import { USER } from '../../core/auth/testing';
import { ToastService } from '../../shared/ui/toast.service';
import AccountPage from './account-page';

describe('AccountPage', () => {
  let fixture: ComponentFixture<AccountPage>;
  let el: HTMLElement;
  let auth: Record<'updateProfile' | 'changePassword' | 'logoutOthers', ReturnType<typeof vi.fn>>;
  let toasts: { show: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    const user = signal(USER);
    auth = {
      updateProfile: vi.fn((changes) => {
        user.set({ ...USER, ...changes });
        return of(user());
      }),
      changePassword: vi.fn(() => of(USER)),
      logoutOthers: vi.fn(() => of(undefined)),
    };
    toasts = { show: vi.fn() };
    TestBed.configureTestingModule({
      imports: [AccountPage],
      providers: [
        provideRouter([]),
        { provide: AuthStore, useValue: { ...auth, user } },
        { provide: ToastService, useValue: toasts },
      ],
    });
    fixture = TestBed.createComponent(AccountPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  async function set(selector: string, value: string, event = 'input') {
    const field = el.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
    field.value = value;
    field.dispatchEvent(new Event(event));
    await fixture.whenStable();
  }
  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find((b) =>
      b.textContent?.includes(name),
    )!;

  it('shows the profile with read-only email and currency', () => {
    expect(el.querySelector('.avatar')?.textContent?.trim()).toBe('A');
    expect(el.querySelector<HTMLInputElement>('#account-name')!.value).toBe('Ana');
    expect(el.querySelector<HTMLInputElement>('#account-email')!.readOnly).toBe(true);
    expect(el.querySelector<HTMLSelectElement>('#account-timezone')!.value).toBe('Europe/Lisbon');
    expect(button('Save changes').disabled).toBe(true);
  });

  it('saves only a changed, valid profile', async () => {
    await set('#account-name', '   ');
    expect(button('Save changes').disabled).toBe(true);
    await set('#account-name', ' Ana Silva ');
    await set('#account-timezone', 'Europe/Madrid', 'change');
    button('Save changes').click();
    await fixture.whenStable();

    expect(auth.updateProfile).toHaveBeenCalledWith({
      name: 'Ana Silva',
      timezone: 'Europe/Madrid',
      auto_new_month: false,
    });
    expect(toasts.show).toHaveBeenCalledWith('Profile saved');
    expect(button('Save changes').disabled).toBe(true);
  });

  it('turns on starting each month automatically', async () => {
    const toggle = el.querySelector<HTMLButtonElement>('[aria-labelledby="account-auto-month"]')!;
    expect(toggle.getAttribute('aria-checked')).toBe('false');
    toggle.click();
    await fixture.whenStable();
    expect(toggle.getAttribute('aria-checked')).toBe('true');
    expect(button('Save changes').disabled).toBe(false);
    button('Save changes').click();
    await fixture.whenStable();
    expect(auth.updateProfile).toHaveBeenCalledWith(
      expect.objectContaining({ auto_new_month: true }),
    );
  });

  it('checks the new password live and updates it', async () => {
    await set('#account-current-password', 'Old-pass-1!');
    await set('#account-new-password', 'short');
    expect(el.querySelectorAll('.rule--met').length).toBeLessThan(5);
    expect(button('Update password').disabled).toBe(true);

    await set('#account-new-password', 'New-pass-2!');
    expect(el.querySelectorAll('.rule--met')).toHaveLength(5);
    button('Update password').click();
    await fixture.whenStable();

    expect(auth.changePassword).toHaveBeenCalledWith('Old-pass-1!', 'New-pass-2!');
    expect(toasts.show).toHaveBeenCalledWith('Password updated. Other devices were signed out.');
    expect(el.querySelector<HTMLInputElement>('#account-new-password')!.value).toBe('');
  });

  it('shows why the password could not change', async () => {
    auth.changePassword.mockReturnValueOnce(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 401,
            error: { detail: 'Current password is incorrect' },
          }),
      ),
    );
    await set('#account-current-password', 'wrong');
    await set('#account-new-password', 'New-pass-2!');
    button('Update password').click();
    await fixture.whenStable();
    expect(el.querySelector('#security [role=alert]')?.textContent).toContain(
      'Current password is incorrect',
    );
  });

  it('signs out the other devices', async () => {
    button('Sign out other devices').click();
    await fixture.whenStable();
    expect(auth.logoutOthers).toHaveBeenCalled();
    expect(toasts.show).toHaveBeenCalledWith('Other devices were signed out');
  });
});
