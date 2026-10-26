import { Injectable } from '@angular/core';
import { Translation, TranslocoLoader } from '@jsverse/transloco';
import { from, Observable } from 'rxjs';

import { AppLanguage } from './language.service';

const loaders: Record<AppLanguage, () => Promise<Translation>> = {
  pt: () => import('./translations/pt').then((m) => m.pt),
  en: () => import('./translations/en').then((m) => m.en),
};

@Injectable({ providedIn: 'root' })
export class TranslationLoader implements TranslocoLoader {
  getTranslation(lang: string): Observable<Translation> {
    const load = loaders[lang as AppLanguage] ?? loaders.pt;
    return from(load());
  }
}
