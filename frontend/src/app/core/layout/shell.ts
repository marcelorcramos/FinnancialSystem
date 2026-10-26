import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TranslocoPipe } from '@jsverse/transloco';

import { ScreenService } from '../../shared/layout/screen.service';
import { AuthStore } from '../auth/auth-store';
import { LanguageMenu } from './language-menu';
import { NAV_ITEMS } from './nav-items';
import { ThemeMenu } from './theme-menu';

/**
 * App frame for signed-in pages.
 * - phone: top bar with a menu button opening the navigation as an overlay
 * - tablet: navigation rail (icons, labels as tooltips)
 * - desktop: full side navigation
 */
@Component({
  selector: 'app-shell',
  imports: [
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatMenuModule,
    MatSidenavModule,
    MatToolbarModule,
    MatTooltipModule,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslocoPipe,
    LanguageMenu,
    ThemeMenu,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  protected readonly screen = inject(ScreenService);
  protected readonly auth = inject(AuthStore);
  protected readonly navItems = NAV_ITEMS;

  protected logout(): void {
    this.auth.logout().subscribe();
  }
}
