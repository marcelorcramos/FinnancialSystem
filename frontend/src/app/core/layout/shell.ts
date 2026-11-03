import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { ChangeDetectionStrategy, Component, computed, effect, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { Icon } from '../../shared/ui/icon';
import { ToastOutlet } from '../../shared/ui/toast-outlet';
import { APP_NAME } from '../app-title-strategy';
import { alertText, AlertsService } from '../alerts/alerts.service';
import { AuthStore } from '../auth/auth-store';
import { NAV_ITEMS } from './nav-items';
import { ThemeToggle } from './theme-toggle';

/**
 * App frame for signed-in pages: a top bar with the brand, the main
 * navigation, the theme toggle and the account menu. On narrow screens the
 * navigation wraps under the brand.
 */
@Component({
  selector: 'app-shell',
  imports: [
    CdkMenu,
    CdkMenuItem,
    CdkMenuTrigger,
    Icon,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    ThemeToggle,
    ToastOutlet,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  protected readonly auth = inject(AuthStore);
  protected readonly alerts = inject(AlertsService);
  protected readonly alertText = alertText;
  protected readonly bellLabel = computed(() => {
    const count = this.alerts.unseen();
    return count ? `Alerts, ${count} new` : 'Alerts';
  });
  protected readonly navItems = NAV_ITEMS;
  protected readonly appName = APP_NAME;
  protected readonly initials = computed(() =>
    (this.auth.user()?.name ?? '')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]!.toUpperCase())
      .join(''),
  );

  constructor() {
    // Alerts stream only while signed in.
    effect(() => (this.auth.isAuthenticated() ? this.alerts.start() : this.alerts.stop()));
  }

  protected monthPath(year: number, month: number): string {
    return `/month/${year}/${month}`;
  }

  protected logout(): void {
    this.auth.logout().subscribe();
  }
}
