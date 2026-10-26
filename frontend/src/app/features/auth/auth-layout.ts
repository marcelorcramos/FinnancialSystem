import { ChangeDetectionStrategy, Component } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';

import { LanguageMenu } from '../../core/layout/language-menu';
import { ThemeMenu } from '../../core/layout/theme-menu';

@Component({
  selector: 'app-auth-layout',
  imports: [MatIconModule, RouterOutlet, TranslocoPipe, LanguageMenu, ThemeMenu],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="top">
      <span class="brand">
        <mat-icon aria-hidden="true">account_balance_wallet</mat-icon>
        {{ 'app.name' | transloco }}
      </span>
      <span class="actions">
        <app-language-menu />
        <app-theme-menu />
      </span>
    </header>
    <main class="main">
      <router-outlet />
    </main>
  `,
  styleUrl: './auth-layout.scss',
})
export class AuthLayout {}
