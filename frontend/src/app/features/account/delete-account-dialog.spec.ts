import { DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { AuthStore } from '../../core/auth/auth-store';
import { DeleteAccountDialog } from './delete-account-dialog';

describe('DeleteAccountDialog', () => {
  let fixture: ComponentFixture<DeleteAccountDialog>;
  let el: HTMLElement;
  let deleteAccount: ReturnType<typeof vi.fn>;
  let close: ReturnType<typeof vi.fn>;

  async function render(reply: unknown = of(undefined)) {
    deleteAccount = vi.fn(() => reply);
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [DeleteAccountDialog],
      providers: [
        { provide: AuthStore, useValue: { deleteAccount } },
        { provide: DialogRef, useValue: { close } },
      ],
    });
    fixture = TestBed.createComponent(DeleteAccountDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function fill(password: string, understood: boolean) {
    const input = el.querySelector<HTMLInputElement>('#delete-password')!;
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
    expect(deleteAccount).toHaveBeenCalledWith('Secret-1');
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
});
