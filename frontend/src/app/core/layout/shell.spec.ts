import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';

import { provideTestI18n } from '../../../testing/i18n';
import { PHONE_QUERY, TABLET_QUERY } from '../../shared/layout/breakpoints';
import { AuthStore } from '../auth/auth-store';
import { USER } from '../auth/testing';
import { Shell } from './shell';

describe('Shell', () => {
  let fixture: ComponentFixture<Shell>;
  let el: HTMLElement;
  let breakpoints: BehaviorSubject<BreakpointState>;
  const logout = vi.fn(() => of(undefined));

  function screen(size: 'phone' | 'tablet' | 'desktop'): BreakpointState {
    return {
      matches: size !== 'desktop',
      breakpoints: { [PHONE_QUERY]: size === 'phone', [TABLET_QUERY]: size === 'tablet' },
    };
  }

  async function render(size: 'phone' | 'tablet' | 'desktop') {
    breakpoints = new BehaviorSubject(screen(size));
    TestBed.configureTestingModule({
      imports: [Shell, provideTestI18n()],
      providers: [
        provideRouter([]),
        { provide: BreakpointObserver, useValue: { observe: () => breakpoints } },
        { provide: AuthStore, useValue: { user: signal(USER), logout } },
      ],
    });
    fixture = TestBed.createComponent(Shell);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const menuButton = () => el.querySelector('button[aria-label="Abrir menu"]');
  const navTitles = () => el.querySelectorAll('mat-nav-list [matListItemTitle]');

  it('shows the full side navigation on desktop', async () => {
    await render('desktop');

    expect(menuButton()).toBeNull();
    expect(navTitles()[0]?.textContent?.trim()).toBe('Início');
    expect(el.querySelector('.shell--rail')).toBeNull();
  });

  it('collapses the navigation into a rail on tablet', async () => {
    await render('tablet');

    expect(el.querySelector('.shell--rail')).not.toBeNull();
    expect(navTitles().length).toBe(0);
    expect(el.querySelector('mat-nav-list a')?.getAttribute('aria-label')).toBe('Início');
  });

  it('uses a menu button and an overlay navigation on phones', async () => {
    await render('phone');

    expect(menuButton()).not.toBeNull();
    expect(el.querySelector('mat-sidenav')?.classList).toContain('mat-drawer-over');
  });

  it('reacts to screen size changes', async () => {
    await render('desktop');
    breakpoints.next(screen('phone'));
    await fixture.whenStable();

    expect(menuButton()).not.toBeNull();
  });

  it('has a skip link to the main content', async () => {
    await render('desktop');

    expect(el.querySelector('a.skip-link')?.getAttribute('href')).toBe('#main');
    expect(el.querySelector('main#main')).not.toBeNull();
  });
});
