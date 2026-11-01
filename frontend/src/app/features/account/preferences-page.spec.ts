import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { DisplayPreferencesService } from '../../core/preferences/display-preferences';
import { ThemeService } from '../../core/theme/theme.service';
import PreferencesPage from './preferences-page';

describe('PreferencesPage', () => {
  let fixture: ComponentFixture<PreferencesPage>;
  let el: HTMLElement;
  const root = document.documentElement;

  beforeEach(async () => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [PreferencesPage], providers: [provideRouter([])] });
    TestBed.inject(ThemeService).init();
    TestBed.inject(DisplayPreferencesService).init();
    fixture = TestBed.createComponent(PreferencesPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.textContent?.trim() === name,
    )!;
  const switchFor = (title: string) => {
    const id = [...el.querySelectorAll('.switch-row__title')].find(
      (t) => t.textContent?.trim() === title,
    )!.id;
    return el.querySelector<HTMLButtonElement>(`[aria-labelledby="${id}"]`)!;
  };

  it('changes the theme and the text size for the whole app', async () => {
    expect(button('Dark').getAttribute('aria-pressed')).toBe('true');
    button('Light').click();
    button('Larger').click();
    await fixture.whenStable();
    expect(root.getAttribute('data-theme')).toBe('light');
    expect(root.getAttribute('data-text-size')).toBe('larger');
    expect(button('Larger').getAttribute('aria-pressed')).toBe('true');
  });

  it('switches motion, contrast and chart patterns', async () => {
    expect(switchFor('Patterns in charts').getAttribute('aria-checked')).toBe('true');
    expect(el.querySelectorAll('.preview__chart rect[fill^="url"]')).toHaveLength(2);

    switchFor('Reduce motion').click();
    switchFor('High contrast').click();
    switchFor('Patterns in charts').click();
    await fixture.whenStable();

    expect(root.hasAttribute('data-reduce-motion')).toBe(true);
    expect(root.hasAttribute('data-high-contrast')).toBe(true);
    expect(root.hasAttribute('data-patterns')).toBe(false);
    expect(switchFor('Reduce motion').getAttribute('aria-checked')).toBe('true');
    expect(el.querySelectorAll('.preview__chart rect[fill^="url"]')).toHaveLength(0);
    expect(el.querySelector('.preview')?.textContent).toContain('Animations off.');
  });

  it('lists the keyboard shortcuts', () => {
    expect(
      [...el.querySelectorAll('.keys li')].map((li) => li.textContent?.replace(/\s+/g, ' ').trim()),
    ).toEqual([
      'N New entry',
      'T Transfer',
      '← → Previous / next month',
      '⌘/Ctrl Z Undo the last delete',
    ]);
  });
});
