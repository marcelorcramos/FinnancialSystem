import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { AuthApi } from '../../../core/auth/auth-api';
import { SignInResult } from '../../../core/auth/auth.models';
import { USER } from '../../../core/auth/testing';
import LoginPage from './login-page';

describe('LoginPage', () => {
  let fixture: ComponentFixture<LoginPage>;
  let el: HTMLElement;
  let login$: Subject<SignInResult>;
  let store: {
    login: ReturnType<typeof vi.fn>;
    sessionExpired: ReturnType<typeof signal<boolean>>;
  };
  let navigate: ReturnType<typeof vi.spyOn>;
  let providers$: Subject<{ google: boolean }>;

  beforeEach(async () => {
    login$ = new Subject<SignInResult>();
    providers$ = new Subject<{ google: boolean }>();
    store = { login: vi.fn(() => login$), sessionExpired: signal(false) };
    TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideRouter([]),
        { provide: AuthStore, useValue: store },
        { provide: AuthApi, useValue: { providers: () => providers$ } },
      ],
    });
    navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture = TestBed.createComponent(LoginPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  function type(selector: string, value: string) {
    const input = el.querySelector<HTMLInputElement>(selector)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  async function submit() {
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('shows validation errors and does not call the API when invalid', async () => {
    await submit();

    expect(store.login).not.toHaveBeenCalled();
    const errors = [...el.querySelectorAll('.field__error')].map((e) => e.textContent?.trim());
    expect(errors).toEqual(['This field is required.', 'This field is required.']);
  });

  it('logs in and goes to the return URL', async () => {
    fixture.componentRef.setInput('returnUrl', '/months');
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'secret123');
    await submit();

    expect(store.login).toHaveBeenCalledWith({ email: USER.email, password: 'secret123' });
    expect(el.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(true);

    login$.next({ user: USER });
    login$.complete();
    await fixture.whenStable();
    expect(navigate).toHaveBeenCalledWith('/months');
  });

  it('ignores external return URLs', async () => {
    fixture.componentRef.setInput('returnUrl', 'https://evil.example');
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'secret123');
    await submit();
    login$.next({ user: USER });
    login$.complete();

    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('shows a message for wrong credentials', async () => {
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'wrong');
    await submit();
    login$.error(new HttpErrorResponse({ status: 401 }));
    await fixture.whenStable();

    expect(el.querySelector('[role=alert]')?.textContent).toContain('Incorrect email or password.');
    expect(el.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(false);
    expect(navigate).not.toHaveBeenCalled();
  });

  it('tells the user when the session expired', async () => {
    store.sessionExpired.set(true);
    await fixture.whenStable();

    expect(el.querySelector('[role=status]')?.textContent).toContain('Your session has expired');
  });

  it('toggles password visibility', async () => {
    const input = el.querySelector<HTMLInputElement>('input[formControlName=password]')!;
    expect(input.type).toBe('password');

    el.querySelector<HTMLButtonElement>('button[aria-label="Show password"]')!.click();
    await fixture.whenStable();
    expect(input.type).toBe('text');
  });

  it('goes to the code step when the account has two-factor sign-in', async () => {
    const go = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    fixture.componentRef.setInput('returnUrl', '/reports');
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'secret123');
    await submit();
    login$.next({ ticket: 'tk' });
    login$.complete();
    await fixture.whenStable();
    expect(go).toHaveBeenCalledWith(['/auth/two-factor'], {
      queryParams: { returnUrl: '/reports' },
    });
  });

  it('shows the Google button only when the server offers it', async () => {
    expect(el.textContent).not.toContain('Continue with Google');
    providers$.next({ google: true });
    await fixture.whenStable();
    const link = [...el.querySelectorAll('a')].find((a) => a.textContent?.includes('Google'));
    expect(link?.getAttribute('href')).toBe('/api/v1/auth/google/login');
  });

  it('explains a failed Google sign-in', async () => {
    fixture.componentRef.setInput('error', 'google');
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain(
      'Signing in with Google did not work',
    );
  });
});
