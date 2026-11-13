import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { AuthStore } from '../auth/auth-store';
import { USER } from '../auth/testing';
import { DemoBanner } from './demo-banner';

describe('DemoBanner', () => {
  async function render(demoExpiresAt: string | null) {
    const logout = vi.fn(() => of(undefined));
    TestBed.configureTestingModule({
      imports: [DemoBanner],
      providers: [
        {
          provide: AuthStore,
          useValue: { user: signal({ ...USER, demo_expires_at: demoExpiresAt }), logout },
        },
      ],
    });
    const fixture = TestBed.createComponent(DemoBanner);
    await fixture.whenStable();
    return { el: fixture.nativeElement as HTMLElement, logout };
  }

  it('says how long the demo lasts and leads to a real account', async () => {
    const inFiveHours = new Date(Date.now() + 4.5 * 3_600_000).toISOString();
    const { el, logout } = await render(inFiveHours);
    expect(el.textContent).toContain('it is deleted in 5 hours');
    el.querySelector('button')!.click();
    expect(logout).toHaveBeenCalledWith('/auth/register');
  });

  it('is hidden for real accounts', async () => {
    const { el } = await render(null);
    expect(el.querySelector('.banner')).toBeNull();
  });
});
