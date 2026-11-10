import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { AuthApi } from '../../../core/auth/auth-api';
import ForgotPasswordPage from './forgot-password-page';

describe('ForgotPasswordPage', () => {
  let fixture: ComponentFixture<ForgotPasswordPage>;
  let el: HTMLElement;
  let api: { requestPasswordReset: ReturnType<typeof vi.fn> };

  async function render(reply = of(undefined as void)) {
    api = { requestPasswordReset: vi.fn(() => reply) };
    TestBed.configureTestingModule({
      imports: [ForgotPasswordPage],
      providers: [provideRouter([]), { provide: AuthApi, useValue: api }],
    });
    fixture = TestBed.createComponent(ForgotPasswordPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function submit(email: string) {
    const input = el.querySelector<HTMLInputElement>('#forgot-email')!;
    input.value = email;
    input.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('asks for a valid email first', async () => {
    await render();
    await submit('not-an-email');
    expect(api.requestPasswordReset).not.toHaveBeenCalled();
    expect(el.querySelector('.field__error')).not.toBeNull();
  });

  it('sends the link and says so without revealing whether the account exists', async () => {
    const reply = new Subject<void>();
    await render(reply);
    await submit(' ana@example.com ');
    expect(api.requestPasswordReset).toHaveBeenCalledWith('ana@example.com');
    reply.next();
    reply.complete();
    await fixture.whenStable();
    expect(el.querySelector('[role=status]')?.textContent).toContain(
      'If ana@example.com has an account, a link to choose a new password is on its way.',
    );
  });

  it('shows the API message when it fails', async () => {
    await render(
      throwError(
        () => new HttpErrorResponse({ status: 429, error: { detail: 'Too many attempts.' } }),
      ),
    );
    await submit('ana@example.com');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Too many attempts.');
  });
});
