import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject } from 'rxjs';

import { provideTestI18n } from '../../../../testing/i18n';
import { AuthStore } from '../../../core/auth/auth-store';
import { UserRead } from '../../../core/auth/auth.models';
import { USER } from '../../../core/auth/testing';
import LoginPage from './login-page';

describe('LoginPage', () => {
  let fixture: ComponentFixture<LoginPage>;
  let el: HTMLElement;
  let login$: Subject<UserRead>;
  let store: { login: ReturnType<typeof vi.fn>; sessionExpired: ReturnType<typeof signal<boolean>> };
  let navigate: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    login$ = new Subject<UserRead>();
    store = { login: vi.fn(() => login$), sessionExpired: signal(false) };
    TestBed.configureTestingModule({
      imports: [LoginPage, provideTestI18n()],
      providers: [provideRouter([]), { provide: AuthStore, useValue: store }],
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
    const errors = [...el.querySelectorAll('mat-error')].map((e) => e.textContent?.trim());
    expect(errors).toEqual(['Campo obrigatório.', 'Campo obrigatório.']);
  });

  it('logs in and goes to the return URL', async () => {
    fixture.componentRef.setInput('returnUrl', '/months');
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'secret123');
    await submit();

    expect(store.login).toHaveBeenCalledWith({ email: USER.email, password: 'secret123' });
    expect(el.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(true);

    login$.next(USER);
    login$.complete();
    await fixture.whenStable();
    expect(navigate).toHaveBeenCalledWith('/months');
  });

  it('ignores external return URLs', async () => {
    fixture.componentRef.setInput('returnUrl', 'https://evil.example');
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'secret123');
    await submit();
    login$.next(USER);
    login$.complete();

    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('shows a message for wrong credentials', async () => {
    type('input[formControlName=email]', USER.email);
    type('input[formControlName=password]', 'wrong');
    await submit();
    login$.error(new HttpErrorResponse({ status: 401 }));
    await fixture.whenStable();

    expect(el.querySelector('[role=alert]')?.textContent).toContain('Email ou password incorretos.');
    expect(el.querySelector<HTMLButtonElement>('button[type=submit]')!.disabled).toBe(false);
    expect(navigate).not.toHaveBeenCalled();
  });

  it('tells the user when the session expired', async () => {
    store.sessionExpired.set(true);
    await fixture.whenStable();

    expect(el.querySelector('[role=status]')?.textContent).toContain('A tua sessão expirou');
  });

  it('toggles password visibility', async () => {
    const input = el.querySelector<HTMLInputElement>('input[formControlName=password]')!;
    expect(input.type).toBe('password');

    el.querySelector<HTMLButtonElement>('button[matSuffix]')!.click();
    await fixture.whenStable();
    expect(input.type).toBe('text');
  });
});
