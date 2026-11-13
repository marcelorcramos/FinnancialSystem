import { DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../core/auth/auth-store';
import { USER } from '../../core/auth/testing';
import { DeleteAccountDialog } from './delete-account-dialog';

describe('DeleteAccountDialog', () => {
  let fixture: ComponentFixture<DeleteAccountDialog>;
  let el: HTMLElement;
  let deleteAccount: ReturnType<typeof vi.fn>;
  let close: ReturnType<typeof vi.fn>;

  async function render(reply: unknown = of(undefined), user = USER) {
    deleteAccount = vi.fn(() => reply);
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [DeleteAccountDialog],
      providers: [
        { provide: AuthStore, useValue: { deleteAccount, user: signal(user) } },
        { provide: DialogRef, useValue: { close } },
      ],
    });
    fixture = TestBed.createComponent(DeleteAccountDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function fill(password: string, understood: boolean, field = '#delete-password') {
    const input = el.querySelector<HTMLInputElement>(field)!;
    input.value = password;
    input.dispatchEvent(new Event('input'));
    const check = el.querySelector<HTMLInputElement>('input[type=checkbox]')!;
    check.checked = understood;
    check.dispatchEvent(new Event('change'));
    await fixture.whenStable();
  }

  const submit = () => el.querySelector<HTMLButtonElement>('button[type=submit]')!;

  it('needs the password and the confirmation', async () => {
    await render();
    await fill('Secret-1', false);
    expect(submit().disabled).toBe(true);
    await fill('Secret-1', true);
    expect(submit().disabled).toBe(false);

    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(deleteAccount).toHaveBeenCalledWith({ password: 'Secret-1' });
    expect(close).toHaveBeenCalledWith(true);
  });

  it('shows a wrong password and stays open', async () => {
    await render(
      throwError(
        () => new HttpErrorResponse({ status: 401, error: { detail: 'Password is incorrect' } }),
      ),
    );
    await fill('nope', true);
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Password is incorrect');
    expect(close).not.toHaveBeenCalled();
  });

  it('asks accounts without a password to type their email', async () => {
    await render(of(undefined), { ...USER, has_password: false, google_linked: true });
    expect(el.querySelector('#delete-password')).toBeNull();
    expect(el.textContent).toContain(`Type your email (${USER.email}) to confirm`);
    await fill(USER.email, true, '#delete-email');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
    expect(deleteAccount).toHaveBeenCalledWith({ confirm_email: USER.email });
  });
});
