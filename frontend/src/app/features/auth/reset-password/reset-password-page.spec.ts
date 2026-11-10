import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthApi } from '../../../core/auth/auth-api';
import { AuthStore } from '../../../core/auth/auth-store';
import { ToastService } from '../../../shared/ui/toast.service';
import ResetPasswordPage from './reset-password-page';

describe('ResetPasswordPage', () => {
  let fixture: ComponentFixture<ResetPasswordPage>;
  let el: HTMLElement;
  let api: { resetPassword: ReturnType<typeof vi.fn> };
  let store: { expireSession: ReturnType<typeof vi.fn> };

  async function render(token: string | undefined, reply: unknown = of(undefined)) {
    api = { resetPassword: vi.fn(() => reply) };
    store = { expireSession: vi.fn() };
    TestBed.configureTestingModule({
      imports: [ResetPasswordPage],
      providers: [
        provideRouter([]),
        { provide: AuthApi, useValue: api },
        { provide: AuthStore, useValue: store },
      ],
    });
    fixture = TestBed.createComponent(ResetPasswordPage);
    if (token) fixture.componentRef.setInput('token', token);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function submit(password: string) {
    const input = el.querySelector<HTMLInputElement>('#reset-password')!;
    input.value = password;
    input.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('offers a new link when the page opens without a token', async () => {
    await render(undefined);
    expect(el.querySelector('[role=alert]')?.textContent).toContain('invalid or has expired');
    expect(el.querySelector('a')?.getAttribute('href')).toBe('/auth/forgot-password');
  });

  it('checks the password rules before sending', async () => {
    await render('tok');
    await submit('short');
    expect(api.resetPassword).not.toHaveBeenCalled();
  });

  it('sets the new password, ends this session and goes to sign in', async () => {
    await render('tok');
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const toast = vi.spyOn(TestBed.inject(ToastService), 'show');
    await submit('New-password-1');
    expect(api.resetPassword).toHaveBeenCalledWith('tok', 'New-password-1');
    expect(store.expireSession).toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith('Password changed. Sign in with the new one.');
    expect(navigate).toHaveBeenCalledWith('/auth/login');
  });

  it('says the link expired when the API refuses the token', async () => {
    await render(
      'old',
      throwError(
        () => new HttpErrorResponse({ status: 422, error: { code: 'invalid_token', detail: 'x' } }),
      ),
    );
    await submit('New-password-1');
    expect(el.querySelector('form')).toBeNull();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('invalid or has expired');
  });
});
