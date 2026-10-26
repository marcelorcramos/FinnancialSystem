import { DOCUMENT, inject, Injectable, signal } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';
import { firstValueFrom } from 'rxjs';

import { readPreference, writePreference } from '../storage/preferences';

export const LANGUAGES = ['pt', 'en'] as const;
export type AppLanguage = (typeof LANGUAGES)[number];
export const DEFAULT_LANGUAGE: AppLanguage = 'pt';

const STORAGE_KEY = 'fs.language';
const HTML_LANG: Record<AppLanguage, string> = { pt: 'pt-PT', en: 'en' };

export function isAppLanguage(value: unknown): value is AppLanguage {
  return typeof value === 'string' && (LANGUAGES as readonly string[]).includes(value);
}

@Injectable({ providedIn: 'root' })
export class LanguageService {
  private readonly transloco = inject(TranslocoService);
  private readonly document = inject(DOCUMENT);

  private readonly _language = signal<AppLanguage>(DEFAULT_LANGUAGE);
  readonly language = this._language.asReadonly();

  /** Picks the stored or browser language and waits for its translations. */
  init(): Promise<unknown> {
    const lang = this.detect();
    this.apply(lang);
    return firstValueFrom(this.transloco.load(lang));
  }

  setLanguage(lang: AppLanguage): void {
    this.apply(lang);
    writePreference(STORAGE_KEY, lang);
  }

  private apply(lang: AppLanguage): void {
    this._language.set(lang);
    this.transloco.setActiveLang(lang);
    this.document.documentElement.lang = HTML_LANG[lang];
  }

  private detect(): AppLanguage {
    const stored = readPreference(STORAGE_KEY);
    if (isAppLanguage(stored)) {
      return stored;
    }
    const browser = this.document.defaultView?.navigator.language ?? '';
    return browser.toLowerCase().startsWith('en') ? 'en' : DEFAULT_LANGUAGE;
  }
}
