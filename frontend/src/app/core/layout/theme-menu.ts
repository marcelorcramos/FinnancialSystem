import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslocoPipe } from '@jsverse/transloco';

import { THEME_MODES, ThemeMode, ThemeService } from '../theme/theme.service';

const ICONS: Record<ThemeMode, string> = {
  system: 'contrast',
  light: 'light_mode',
  dark: 'dark_mode',
};

@Component({
  selector: 'app-theme-menu',
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule, TranslocoPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      mat-icon-button
      [matMenuTriggerFor]="menu"
      [matTooltip]="'theme.label' | transloco"
      [attr.aria-label]="'theme.label' | transloco"
    >
      <mat-icon>{{ icon() }}</mat-icon>
    </button>
    <mat-menu #menu="matMenu">
      @for (mode of modes; track mode) {
        <button
          mat-menu-item
          role="menuitemradio"
          [attr.aria-checked]="theme.mode() === mode"
          (click)="theme.setMode(mode)"
        >
          <mat-icon>{{ icons[mode] }}</mat-icon>
          <span>{{ 'theme.' + mode | transloco }}</span>
          @if (theme.mode() === mode) {
            <mat-icon class="check" aria-hidden="true">check</mat-icon>
          }
        </button>
      }
    </mat-menu>
  `,
  styles: `
    .check {
      margin-inline-start: var(--space-4);
      margin-inline-end: 0;
    }
  `,
})
export class ThemeMenu {
  protected readonly theme = inject(ThemeService);
  protected readonly modes = THEME_MODES;
  protected readonly icons = ICONS;
  protected readonly icon = computed(() => ICONS[this.theme.mode()]);
}
