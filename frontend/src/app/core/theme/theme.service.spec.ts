import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    root.removeAttribute('data-theme');
  });

  it('follows the system by default', () => {
    const service = TestBed.inject(ThemeService);
    service.init();

    expect(service.mode()).toBe('system');
    expect(root.hasAttribute('data-theme')).toBe(false);
  });

  it('applies and remembers an explicit mode', () => {
    const service = TestBed.inject(ThemeService);
    service.setMode('dark');

    expect(root.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem('fs.theme')).toBe('dark');
  });

  it('restores the stored mode on init', () => {
    localStorage.setItem('fs.theme', 'light');
    const service = TestBed.inject(ThemeService);
    service.init();

    expect(service.mode()).toBe('light');
    expect(root.getAttribute('data-theme')).toBe('light');
  });

  it('ignores invalid stored values and forgets the choice when back to system', () => {
    localStorage.setItem('fs.theme', 'neon');
    const service = TestBed.inject(ThemeService);
    service.init();
    expect(service.mode()).toBe('system');

    service.setMode('dark');
    service.setMode('system');
    expect(root.hasAttribute('data-theme')).toBe(false);
    expect(localStorage.getItem('fs.theme')).toBeNull();
  });
});
