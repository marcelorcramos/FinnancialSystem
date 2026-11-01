import { DOCUMENT, inject, Injectable, signal } from '@angular/core';

import { readPreference, writePreference } from '../storage/preferences';

export const TEXT_SIZES = ['default', 'large', 'larger'] as const;
export type TextSize = (typeof TEXT_SIZES)[number];

export interface DisplayPreferences {
  textSize: TextSize;
  reduceMotion: boolean;
  highContrast: boolean;
  /** Stripes and dots on the kind colours, so charts never rely on colour alone. */
  patterns: boolean;
}

const DEFAULTS: DisplayPreferences = {
  textSize: 'default',
  reduceMotion: false,
  highContrast: false,
  patterns: true,
};

const KEYS: Record<keyof DisplayPreferences, string> = {
  textSize: 'fs.display.text-size',
  reduceMotion: 'fs.display.reduce-motion',
  highContrast: 'fs.display.high-contrast',
  patterns: 'fs.display.patterns',
};

function stored(): DisplayPreferences {
  const size = readPreference(KEYS.textSize);
  const flag = (key: keyof DisplayPreferences, fallback: boolean) => {
    const value = readPreference(KEYS[key]);
    return value === null ? fallback : value === 'on';
  };
  return {
    textSize: (TEXT_SIZES as readonly string[]).includes(size ?? '')
      ? (size as TextSize)
      : DEFAULTS.textSize,
    reduceMotion: flag('reduceMotion', DEFAULTS.reduceMotion),
    highContrast: flag('highContrast', DEFAULTS.highContrast),
    patterns: flag('patterns', DEFAULTS.patterns),
  };
}

/**
 * Per-browser display and accessibility preferences. Each one is a `data-*`
 * attribute on <html> that the design tokens react to (see _tokens.scss).
 */
@Injectable({ providedIn: 'root' })
export class DisplayPreferencesService {
  private readonly document = inject(DOCUMENT);
  private readonly _current = signal<DisplayPreferences>(DEFAULTS);
  readonly current = this._current.asReadonly();

  init(): void {
    this.apply(stored());
  }

  set<K extends keyof DisplayPreferences>(key: K, value: DisplayPreferences[K]): void {
    this.apply({ ...this._current(), [key]: value });
    const isDefault = value === DEFAULTS[key];
    const text = typeof value === 'boolean' ? (value ? 'on' : 'off') : String(value);
    writePreference(KEYS[key], isDefault ? null : text);
  }

  private apply(preferences: DisplayPreferences): void {
    this._current.set(preferences);
    const root = this.document.documentElement;
    root.setAttribute('data-text-size', preferences.textSize);
    root.toggleAttribute('data-reduce-motion', preferences.reduceMotion);
    root.toggleAttribute('data-high-contrast', preferences.highContrast);
    root.toggleAttribute('data-patterns', preferences.patterns);
  }
}
