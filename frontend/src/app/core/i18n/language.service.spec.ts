import { TestBed } from '@angular/core/testing';
import { TranslocoService } from '@jsverse/transloco';

import { provideTestI18n } from '../../../testing/i18n';
import { LanguageService } from './language.service';

describe('LanguageService', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({ imports: [provideTestI18n()] });
  });

  afterEach(() => vi.restoreAllMocks());

  it('defaults to Portuguese', async () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('pt-PT');
    const service = TestBed.inject(LanguageService);
    await service.init();

    expect(service.language()).toBe('pt');
    expect(document.documentElement.lang).toBe('pt-PT');
  });

  it('uses English when the browser prefers it', async () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('en-GB');
    const service = TestBed.inject(LanguageService);
    await service.init();

    expect(service.language()).toBe('en');
    expect(TestBed.inject(TranslocoService).getActiveLang()).toBe('en');
  });

  it('switches language, translates and remembers the choice', async () => {
    const service = TestBed.inject(LanguageService);
    await service.init();
    service.setLanguage('en');

    expect(TestBed.inject(TranslocoService).translate('kind.saving')).toBe('Saving');
    expect(document.documentElement.lang).toBe('en');
    expect(localStorage.getItem('fs.language')).toBe('en');
  });

  it('prefers the stored language over the browser one', async () => {
    localStorage.setItem('fs.language', 'en');
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('pt-PT');
    const service = TestBed.inject(LanguageService);
    await service.init();

    expect(service.language()).toBe('en');
  });
});
