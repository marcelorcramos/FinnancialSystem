import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ThemeService } from '../theme/theme.service';
import { ThemeToggle } from './theme-toggle';

describe('ThemeToggle', () => {
  let fixture: ComponentFixture<ThemeToggle>;
  let theme: ThemeService;

  beforeEach(async () => {
    localStorage.clear();
    theme = TestBed.inject(ThemeService);
    theme.init();
    fixture = TestBed.createComponent(ThemeToggle);
    await fixture.whenStable();
  });

  const button = () => fixture.nativeElement.querySelector('button') as HTMLButtonElement;

  it('cycles dark, light and system', async () => {
    expect(button().getAttribute('aria-label')).toBe('Theme: Dark. Switch to Light');

    button().click();
    await fixture.whenStable();
    expect(theme.mode()).toBe('light');
    expect(button().getAttribute('aria-label')).toBe('Theme: Light. Switch to System');

    button().click();
    button().click();
    expect(theme.mode()).toBe('dark');
  });
});
