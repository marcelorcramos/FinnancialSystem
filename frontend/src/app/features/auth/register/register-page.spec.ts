import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { UserRead } from '../../../core/auth/auth.models';
import { USER } from '../../../core/auth/testing';
import RegisterPage from './register-page';

describe('RegisterPage', () => {
  let fixture: ComponentFixture<RegisterPage>;
  let el: HTMLElement;
  let register$: Subject<UserRead>;
  let store: { register: ReturnType<typeof vi.fn> };
  let navigate: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    register$ = new Subject<UserRead>();
    store = { register: vi.fn(() => register$) };
    TestBed.configureTestingModule({
      imports: [RegisterPage],
      providers: [provideRouter([]), { provide: AuthStore, useValue: store }],
    });
    navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture = TestBed.createComponent(RegisterPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  function type(name: string, value: string) {
    const input = el.querySelector<HTMLInputElement>(`input[formControlName=${name}]`)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  async function fill(overrides: Record<string, string> = {}) {
    const values = {
      name: ' Ana ',
      email: USER.email,
      password: 'Secret#123',
      confirmPassword: 'Secret#123',
      ...overrides,
    };
    for (const [name, value] of Object.entries(values)) type(name, value);
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  const errors = () => [...el.querySelectorAll('.field__error')].map((e) => e.textContent?.trim());

  it('registers with the trimmed name and goes home', async () => {
    await fill();

    expect(store.register).toHaveBeenCalledWith({
      name: 'Ana',
      email: USER.email,
      password: 'Secret#123',
    });
    register$.next(USER);
    register$.complete();
    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('requires a password with at least 8 characters', async () => {
    await fill({ password: 'short', confirmPassword: 'short' });

    expect(store.register).not.toHaveBeenCalled();
    expect(errors()).toContain(
      'Use at least 8 characters with an uppercase, a lowercase, a number and a symbol.',
    );
  });

  it('requires upper, lower, digit and symbol in the password', async () => {
    await fill({ password: 'segura2026', confirmPassword: 'segura2026' });

    expect(store.register).not.toHaveBeenCalled();
    expect(errors()).toContain(
      'Use at least 8 characters with an uppercase, a lowercase, a number and a symbol.',
    );
  });

  it('requires both passwords to match', async () => {
    await fill({ confirmPassword: 'different1' });

    expect(store.register).not.toHaveBeenCalled();
    expect(errors()).toContain('Passwords do not match.');
  });

  it('ticks the password rules while typing', async () => {
    type('password', 'secure2026');
    await fixture.whenStable();

    const met = [...el.querySelectorAll('.rule')].map((rule) =>
      rule.classList.contains('rule--met'),
    );
    expect(met).toEqual([true, true, false, true, false]);
  });

  it('validates the email', async () => {
    await fill({ email: 'not-an-email' });

    expect(store.register).not.toHaveBeenCalled();
    expect(errors()).toContain('Enter a valid email.');
  });

  it('explains when the email is already registered', async () => {
    await fill();
    register$.error(new HttpErrorResponse({ status: 409 }));
    await fixture.whenStable();

    expect(el.querySelector('[role=alert]')?.textContent).toContain(
      'An account with this email already exists.',
    );
  });
});
