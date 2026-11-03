import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AlertRead } from '../api/types';
import { AlertsService } from '../alerts/alerts.service';
import { AuthStore } from '../auth/auth-store';
import { USER } from '../auth/testing';
import { Shell } from './shell';

describe('Shell', () => {
  let fixture: ComponentFixture<Shell>;
  let el: HTMLElement;
  const logout = vi.fn(() => of(undefined));
  const alertList = signal<AlertRead[]>([]);
  const alerts = {
    alerts: alertList,
    unseen: signal(0),
    start: vi.fn(),
    stop: vi.fn(),
    markAllSeen: vi.fn(),
  };

  beforeEach(async () => {
    logout.mockClear();
    TestBed.configureTestingModule({
      imports: [Shell],
      providers: [
        provideRouter([]),
        {
          provide: AuthStore,
          useValue: { user: signal(USER), isAuthenticated: signal(true), logout },
        },
        { provide: AlertsService, useValue: alerts },
      ],
    });
    fixture = TestBed.createComponent(Shell);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  it('shows the brand and the main navigation', () => {
    expect(el.querySelector('.brand')?.textContent).toContain('FinnancialSystem');
    const links = [...el.querySelectorAll('nav[aria-label=Main] a')];
    expect(links.map((a) => a.textContent?.trim())).toEqual(['Month', 'Reports', 'Labels']);
  });

  it('shows the user initials on the account button', () => {
    expect(el.querySelector('.account__avatar')?.textContent?.trim()).toBe('A');
  });

  it('signs out from the account menu', async () => {
    el.querySelector<HTMLButtonElement>('button[aria-label="Account menu"]')!.click();
    await fixture.whenStable();

    const menu = document.querySelector('.menu')!;
    expect(menu.textContent).toContain(USER.email);
    [...menu.querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.includes('Sign out'))!
      .click();
    expect(logout).toHaveBeenCalled();
  });

  it('has a skip link to the main content', () => {
    expect(el.querySelector('a.skip-link')?.getAttribute('href')).toBe('#main');
    expect(el.querySelector('main#main')).not.toBeNull();
  });

  it('starts the alerts and shows how many are new on the bell', async () => {
    expect(alerts.start).toHaveBeenCalled();
    const bell = el.querySelector<HTMLButtonElement>('.bell')!;
    expect(bell.getAttribute('aria-label')).toBe('Alerts');
    expect(el.querySelector('.bell__badge')).toBeNull();

    alerts.unseen.set(3);
    alertList.set([
      {
        id: 'a1',
        level: 'exceeded',
        label_id: 'food',
        label_name: 'Food',
        color: '#FFB74D',
        month_id: 'm11',
        year: 2026,
        month: 11,
        limit_amount: '300.00',
        total: '320.00',
        seen_at: null,
        created_at: '2026-11-03T20:00:00Z',
      },
    ]);
    await fixture.whenStable();
    expect(bell.getAttribute('aria-label')).toBe('Alerts, 3 new');
    expect(el.querySelector('.bell__badge')?.textContent?.trim()).toBe('3');

    bell.click();
    await fixture.whenStable();
    const item = document.querySelector<HTMLAnchorElement>('.alert')!;
    expect(item.textContent).toContain(
      'Food went over its €300.00 limit in November 2026 (€320.00).',
    );
    expect(item.getAttribute('href')).toBe('/month/2026/11');
  });
});
