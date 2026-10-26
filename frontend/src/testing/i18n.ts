import { ModuleWithProviders } from '@angular/core';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

import { en } from '../app/core/i18n/translations/en';
import { pt } from '../app/core/i18n/translations/pt';

/** Transloco with the real PT/EN dictionaries, loaded synchronously. */
export function provideTestI18n(
  options: TranslocoTestingOptions = {},
): ModuleWithProviders<TranslocoTestingModule> {
  return TranslocoTestingModule.forRoot({
    langs: { pt, en },
    translocoConfig: { availableLangs: ['pt', 'en'], defaultLang: 'pt' },
    preloadLangs: true,
    ...options,
  });
}
