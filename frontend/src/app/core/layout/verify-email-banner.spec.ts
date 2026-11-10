import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { AuthStore } from '../auth/auth-store';
import { UserRead } from '../auth/auth.models';
import { USER } from '../auth/testing';
import { VerifyEmailBanner } from './verify-email-banner';

describe('VerifyEmailBanner', () => {
  let fixture: ComponentFixture<VerifyEmailBanner>;
  let el: HTMLElement;
  let user: ReturnType<typeof signal<UserRead | null>>;
  let resend: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    user = signal<UserRead | null>(USER);
    resend = vi.fn(() => of(undefined));
    TestBed.configureTestingModule({
      imports: [VerifyEmailBanner],
      providers: [{ provide: AuthStore, useValue: { user, resendVerification: resend } }],
    });
    fixture = TestBed.createComponent(VerifyEmailBanner);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  it('reminds an unconfirmed user and sends the link again', async () => {
    expect(el.textContent).toContain('we sent a link to ana@example.com');
    const button = el.querySelector<HTMLButtonElement>('.banner__action')!;
    button.click();
    await fixture.whenStable();
    expect(resend).toHaveBeenCalled();
    expect(button.textContent?.trim()).toBe('Link sent');
    expect(button.disabled).toBe(true);
  });

  it('can be hidden, and is gone once the email is confirmed', async () => {
    el.querySelector<HTMLButtonElement>('[aria-label="Hide this reminder"]')!.click();
    await fixture.whenStable();
    expect(el.querySelector('.banner')).toBeNull();

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [VerifyEmailBanner],
      providers: [
        {
          provide: AuthStore,
          useValue: { user: signal({ ...USER, email_verified_at: '2026-11-10T00:00:00Z' }) },
        },
      ],
    });
    const confirmed = TestBed.createComponent(VerifyEmailBanner);
    await confirmed.whenStable();
    expect(confirmed.nativeElement.querySelector('.banner')).toBeNull();
  });
});
