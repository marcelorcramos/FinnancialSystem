import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AuthStore } from '../auth/auth-store';
import { USER } from '../auth/testing';
import { Shell } from './shell';

describe('Shell', () => {
  let fixture: ComponentFixture<Shell>;
  let el: HTMLElement;
  const logout = vi.fn(() => of(undefined));

  beforeEach(async () => {
    logout.mockClear();
    TestBed.configureTestingModule({
      imports: [Shell],
      providers: [
        provideRouter([]),
        { provide: AuthStore, useValue: { user: signal(USER), logout } },
      ],
    });
    fixture = TestBed.createComponent(Shell);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  it('shows the brand and the main navigation', () => {
    expect(el.querySelector('.brand')?.textContent).toContain('FinnancialSystem');
    const links = [...el.querySelectorAll('nav[aria-label=Main] a')];
    expect(links.map((a) => a.textContent?.trim())).toEqual(['Month', 'Labels']);
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
});
