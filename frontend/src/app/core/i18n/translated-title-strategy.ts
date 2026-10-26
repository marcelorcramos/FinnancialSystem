import { DestroyRef, inject, Injectable } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, TitleStrategy } from '@angular/router';
import { TranslocoService } from '@jsverse/transloco';
import { switchMap } from 'rxjs';

/** Route `title`s are translation keys; the document title follows the language. */
@Injectable()
export class TranslatedTitleStrategy extends TitleStrategy {
  private readonly title = inject(Title);
  private readonly transloco = inject(TranslocoService);
  private lastKey: string | undefined;

  constructor() {
    super();
    this.transloco.langChanges$
      .pipe(
        switchMap((lang) => this.transloco.load(lang)),
        takeUntilDestroyed(inject(DestroyRef)),
      )
      .subscribe(() => this.apply());
  }

  override updateTitle(snapshot: RouterStateSnapshot): void {
    this.lastKey = this.buildTitle(snapshot);
    this.apply();
  }

  private apply(): void {
    const app = this.transloco.translate('app.name');
    this.title.setTitle(this.lastKey ? `${this.transloco.translate(this.lastKey)} · ${app}` : app);
  }
}
