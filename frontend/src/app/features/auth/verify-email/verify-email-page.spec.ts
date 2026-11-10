import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../../core/auth/auth-store';
import VerifyEmailPage from './verify-email-page';

describe('VerifyEmailPage', () => {
  let fixture: ComponentFixture<VerifyEmailPage>;
  let el: HTMLElement;
  let store: Record<string, unknown> & {
    verifyEmail: ReturnType<typeof vi.fn>;
    resendVerification: ReturnType<typeof vi.fn>;
  };

  async function render(token: string | undefined, reply: unknown, signedIn = false) {
    store = {
      isAuthenticated: signal(signedIn),
      restoreSession: vi.fn(() => of(signedIn)),
      verifyEmail: vi.fn(() => reply),
      resendVerification: vi.fn(() => of(undefined)),
    };
    TestBed.configureTestingModule({
      imports: [VerifyEmailPage],
      providers: [provideRouter([]), { provide: AuthStore, useValue: store }],
    });
    fixture = TestBed.createComponent(VerifyEmailPage);
    if (token) fixture.componentRef.setInput('token', token);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  it('confirms the email as soon as the link opens', async () => {
    await render('tok', of(undefined), true);
    expect(store['restoreSession']).toHaveBeenCalled();
    expect(store.verifyEmail).toHaveBeenCalledWith('tok');
    expect(el.querySelector('[role=status]')?.textContent).toContain('Your email is confirmed');
    expect(el.querySelector('a')?.textContent?.trim()).toBe('Continue');
  });

  it('lets a signed-in user ask for a new link when this one expired', async () => {
    const expired = new HttpErrorResponse({
      status: 422,
      error: { detail: 'This link is invalid or has expired. Ask for a new one.' },
    });
    await render(
      'old',
      throwError(() => expired),
      true,
    );
    expect(el.querySelector('[role=alert]')?.textContent).toContain('invalid or has expired');
    el.querySelector<HTMLButtonElement>('button')!.click();
    expect(store.resendVerification).toHaveBeenCalled();
  });

  it('asks a signed-out user to sign in for a new link', async () => {
    await render(undefined, of(undefined));
    expect(store.verifyEmail).not.toHaveBeenCalled();
    expect(el.textContent).toContain('Sign in to ask for a new link.');
  });
});
