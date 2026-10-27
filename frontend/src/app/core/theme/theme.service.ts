import { DOCUMENT, inject, Injectable, signal } from '@angular/core';

import { readPreference, writePreference } from '../storage/preferences';

export const THEME_MODES = ['dark', 'light', 'system'] as const;
export type ThemeMode = (typeof THEME_MODES)[number];

const STORAGE_KEY = 'fs.theme';
const DEFAULT_MODE: ThemeMode = 'dark';

function isThemeMode(value: unknown): value is ThemeMode {
  return typeof value === 'string' && (THEME_MODES as readonly string[]).includes(value);
}

/**
 * Theme mode. The design tokens use `light-dark()`, so switching is a matter of
 * setting `color-scheme` through `data-theme` on <html>. Dark is the default;
 * "system" follows `prefers-color-scheme`.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly document = inject(DOCUMENT);

  private readonly _mode = signal<ThemeMode>(DEFAULT_MODE);
  readonly mode = this._mode.asReadonly();

  init(): void {
    const stored = readPreference(STORAGE_KEY);
    this.apply(isThemeMode(stored) ? stored : DEFAULT_MODE);
  }

  setMode(mode: ThemeMode): void {
    this.apply(mode);
    writePreference(STORAGE_KEY, mode === DEFAULT_MODE ? null : mode);
  }

  private apply(mode: ThemeMode): void {
    this._mode.set(mode);
    this.document.documentElement.setAttribute('data-theme', mode);
  }
}
