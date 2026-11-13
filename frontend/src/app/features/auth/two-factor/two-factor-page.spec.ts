import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import { USER } from '../../../core/auth/testing';
import TwoFactorPage from './two-factor-page';

describe('TwoFactorPage', () => {
  let fixture: ComponentFixture<TwoFactorPage>;
  let el: HTMLElement;
  let store: {
    pendingTicket: ReturnType<typeof signal<string | null>>;
    completeTwoFactor: ReturnType<typeof vi.fn>;
  };

  async function render(ticket: string | null, reply: unknown = of(USER)) {
    store = { pendingTicket: signal(ticket), completeTwoFactor: vi.fn(() => reply) };
    TestBed.configureTestingModule({
      imports: [TwoFactorPage],
      providers: [provideRouter([]), { provide: AuthStore, useValue: store }],
    });
    fixture = TestBed.createComponent(TwoFactorPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function enter(code: string) {
    const input = el.querySelector<HTMLInputElement>('#two-factor-code')!;
    input.value = code;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  }

  const submit = () => el.querySelector<HTMLButtonElement>('button[type=submit]')!;

  it('asks to start again when no sign-in waits for a code', async () => {
    await render(null);
    expect(el.querySelector('[role=alert]')?.textContent).toContain('This sign-in expired');
  });

  it('takes the ticket Google put in the fragment and cleans the address bar', async () => {
    window.location.hash = '#ticket=from-google';
    await render(null);
    expect(store.pendingTicket()).toBe('from-google');
    expect(window.location.hash).toBe('');
  });

  it('sends a 6-digit code and goes to the return URL', async () => {
    await render('tk');
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    fixture.componentRef.setInput('returnUrl', '/reports');
    await enter('12345');
    expect(submit().disabled).toBe(true);
    await enter('123456');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(store.completeTwoFactor).toHaveBeenCalledWith('123456');
    expect(navigate).toHaveBeenCalledWith('/reports');
  });

  it('accepts a recovery code instead', async () => {
    await render('tk');
    [...el.querySelectorAll<HTMLButtonElement>('.link-button')][0]!.click();
    await fixture.whenStable();
    expect(el.querySelector('label')?.textContent).toBe('Recovery code');
    await enter('k7q2m-9xdab');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(store.completeTwoFactor).toHaveBeenCalledWith('k7q2m-9xdab');
  });

  it('shows a wrong code and lets the user try again', async () => {
    await render(
      'tk',
      throwError(
        () => new HttpErrorResponse({ status: 401, error: { detail: 'That code is not valid' } }),
      ),
    );
    await enter('000000');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('That code is not valid');
    expect(store.pendingTicket()).toBe('tk');
  });
});
