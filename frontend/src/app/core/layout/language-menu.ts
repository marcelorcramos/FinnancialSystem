import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoPipe } from '@jsverse/transloco';

import { LanguageService, LANGUAGES } from '../i18n/language.service';

@Component({
  selector: 'app-language-menu',
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule, TranslocoPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      mat-button
      class="trigger"
      [matMenuTriggerFor]="menu"
      [matTooltip]="'language.label' | transloco"
      [attr.aria-label]="'language.label' | transloco"
    >
      <mat-icon>translate</mat-icon>
      {{ language.language().toUpperCase() }}
    </button>
    <mat-menu #menu="matMenu">
      @for (lang of languages; track lang) {
        <button
          mat-menu-item
          role="menuitemradio"
          [attr.lang]="lang"
          [attr.aria-checked]="language.language() === lang"
          (click)="language.setLanguage(lang)"
        >
          <span>{{ 'language.' + lang | transloco }}</span>
          @if (language.language() === lang) {
            <mat-icon class="check" aria-hidden="true">check</mat-icon>
          }
        </button>
      }
    </mat-menu>
  `,
  styles: `
    .trigger {
      min-width: 0;
    }

    .check {
      margin-inline-start: var(--space-4);
      margin-inline-end: 0;
    }
  `,
})
export class LanguageMenu {
  protected readonly language = inject(LanguageService);
  protected readonly languages = LANGUAGES;
}
