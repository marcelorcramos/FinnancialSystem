import { DOCUMENT, inject, Injectable, signal } from '@angular/core';

import { readPreference, writePreference } from '../storage/preferences';

export const THEME_MODES = ['system', 'light', 'dark'] as const;
export type ThemeMode = (typeof THEME_MODES)[number];

const STORAGE_KEY = 'fs.theme';

function isThemeMode(value: unknown): value is ThemeMode {
  return typeof value === 'string' && (THEME_MODES as readonly string[]).includes(value);
}

/**
 * Light/dark mode. Material M3 and the design tokens use `light-dark()`, so
 * switching is a matter of setting `color-scheme` through `data-theme` on <html>.
 * "system" removes the attribute and follows `prefers-color-scheme`.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);

  private readonly _mode = signal<ThemeMode>('system');
  readonly mode = this._mode.asReadonly();

  init(): void {
    const stored = readPreference(STORAGE_KEY);
    this.apply(isThemeMode(stored) ? stored : 'system');
  }

  setMode(mode: ThemeMode): void {
    this.apply(mode);
    writePreference(STORAGE_KEY, mode === 'system' ? null : mode);
  }

  private apply(mode: ThemeMode): void {
    this._mode.set(mode);
    const root = this.document.documentElement;
    if (mode === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', mode);
    }
  }
}
