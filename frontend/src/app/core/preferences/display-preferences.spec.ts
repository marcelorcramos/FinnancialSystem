import { TestBed } from '@angular/core/testing';

import { DisplayPreferencesService } from './display-preferences';

describe('DisplayPreferencesService', () => {
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    for (const name of [
      'data-text-size',
      'data-reduce-motion',
      'data-high-contrast',
      'data-patterns',
    ]) {
      root.removeAttribute(name);
    }
  });

  it('starts with default text, motion on, normal contrast and patterns', () => {
    const service = TestBed.inject(DisplayPreferencesService);
    service.init();
    expect(service.current()).toEqual({
      textSize: 'default',
      reduceMotion: false,
      highContrast: false,
      patterns: true,
    });
    expect(root.getAttribute('data-text-size')).toBe('default');
    expect(root.hasAttribute('data-patterns')).toBe(true);
    expect(root.hasAttribute('data-reduce-motion')).toBe(false);
  });

  it('applies each choice and stores only what differs from the default', () => {
    const service = TestBed.inject(DisplayPreferencesService);
    service.init();
    service.set('textSize', 'larger');
    service.set('reduceMotion', true);
    service.set('patterns', false);

    expect(root.getAttribute('data-text-size')).toBe('larger');
    expect(root.hasAttribute('data-reduce-motion')).toBe(true);
    expect(root.hasAttribute('data-patterns')).toBe(false);
    expect(localStorage.getItem('fs.display.text-size')).toBe('larger');
    expect(localStorage.getItem('fs.display.patterns')).toBe('off');

    service.set('textSize', 'default');
    expect(localStorage.getItem('fs.display.text-size')).toBeNull();
  });

  it('restores stored choices and ignores unknown values', () => {
    localStorage.setItem('fs.display.high-contrast', 'on');
    localStorage.setItem('fs.display.text-size', 'huge');
    const service = TestBed.inject(DisplayPreferencesService);
    service.init();
    expect(service.current().highContrast).toBe(true);
    expect(service.current().textSize).toBe('default');
    expect(root.hasAttribute('data-high-contrast')).toBe(true);
  });
});
