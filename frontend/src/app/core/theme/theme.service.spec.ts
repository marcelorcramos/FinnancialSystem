import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    root.removeAttribute('data-theme');
  });

  it('is dark by default', () => {
    const service = TestBed.inject(ThemeService);
    service.init();

    expect(service.mode()).toBe('dark');
    expect(root.getAttribute('data-theme')).toBe('dark');
  });

  it('applies and remembers an explicit mode', () => {
    const service = TestBed.inject(ThemeService);
    service.setMode('system');

    expect(root.getAttribute('data-theme')).toBe('system');
    expect(localStorage.getItem('fs.theme')).toBe('system');
  });

  it('restores the stored mode on init', () => {
    localStorage.setItem('fs.theme', 'light');
    const service = TestBed.inject(ThemeService);
    service.init();

    expect(service.mode()).toBe('light');
    expect(root.getAttribute('data-theme')).toBe('light');
  });

  it('ignores invalid stored values and forgets the choice when back to dark', () => {
    localStorage.setItem('fs.theme', 'neon');
    const service = TestBed.inject(ThemeService);
    service.init();
    expect(service.mode()).toBe('dark');

    service.setMode('light');
    service.setMode('dark');
    expect(root.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem('fs.theme')).toBeNull();
  });
});
