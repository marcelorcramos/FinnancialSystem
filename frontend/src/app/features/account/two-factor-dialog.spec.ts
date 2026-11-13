import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { TwoFactorApi } from './two-factor-api';
import { TwoFactorDialog, TwoFactorMode } from './two-factor-dialog';

const CODES = Array.from({ length: 10 }, (_, i) => `aaaaa-bbbb${i}`);

describe('TwoFactorDialog', () => {
  let fixture: ComponentFixture<TwoFactorDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(mode: TwoFactorMode) {
    api = {
      setup: vi.fn(() =>
        of({
          secret: 'JBSWY3DPEHPK3PXP',
          otpauth_uri: 'otpauth://x',
          qr_code: 'data:image/svg+xml,x',
        }),
      ),
      enable: vi.fn(() => of({ codes: CODES })),
      disable: vi.fn(() => of(undefined)),
      recoveryCodes: vi.fn(() => of({ codes: CODES })),
    };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [TwoFactorDialog],
      providers: [
        { provide: TwoFactorApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: mode },
      ],
    });
    fixture = TestBed.createComponent(TwoFactorDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function confirm(code: string) {
    const input = el.querySelector<HTMLInputElement>('#two-factor-dialog-code')!;
    input.value = code;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('turns it on: QR code, a code from the app, then the recovery codes', async () => {
    await render('turn-on');
    expect(el.querySelector('img')?.getAttribute('src')).toBe('data:image/svg+xml,x');
    expect(el.querySelector('code')?.textContent).toBe('JBSWY3DPEHPK3PXP');
    await confirm('123456');
    expect(api['enable']).toHaveBeenCalledWith('123456');
    expect(el.querySelectorAll('.codes li').length).toBe(10);
    [...el.querySelectorAll('button')]
      .find((b) => b.textContent?.includes('I saved them'))!
      .click();
    expect(close).toHaveBeenCalledWith(true);
  });

  it('keeps the dialog open on a wrong code', async () => {
    await render('turn-on');
    api['enable']!.mockReturnValue(
      throwError(
        () => new HttpErrorResponse({ status: 401, error: { detail: 'That code is not valid' } }),
      ),
    );
    await confirm('000000');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('That code is not valid');
    expect(close).not.toHaveBeenCalled();
  });

  it('turns it off with a code', async () => {
    await render('turn-off');
    expect(api['setup']).not.toHaveBeenCalled();
    await confirm('654321');
    expect(api['disable']).toHaveBeenCalledWith('654321');
    expect(close).toHaveBeenCalledWith(true);
  });

  it('shows new recovery codes after a code', async () => {
    await render('new-codes');
    await confirm('aaaaa-bbbbb');
    expect(api['recoveryCodes']).toHaveBeenCalledWith('aaaaa-bbbbb');
    expect(el.querySelectorAll('.codes li').length).toBe(10);
  });
});
