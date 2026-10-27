import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { APP_NAME } from '../../core/app-title-strategy';
import { ThemeToggle } from '../../core/layout/theme-toggle';
import { Icon } from '../../shared/ui/icon';

@Component({
  selector: 'app-auth-layout',
  imports: [Icon, RouterLink, RouterLinkActive, RouterOutlet, ThemeToggle],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="intro">
      <span class="brand">
        <app-icon name="logo" [size]="32" />
        {{ appName }}
      </span>
      <div class="pitch">
        <h1>Every euro of the month, in its place.</h1>
        <p>
          Split your income across labels, move money between them and see where it went. You enter
          everything yourself: no bank connection, nothing hidden.
        </p>
      </div>
      <ul class="kinds" aria-label="What you track">
        <li class="kind kind--expense">
          <app-icon name="expense" [size]="18" />
          <span>Spend</span>
        </li>
        <li class="kind kind--saving">
          <app-icon name="saving" [size]="18" />
          <span>Save</span>
        </li>
        <li class="kind kind--investment">
          <app-icon name="investment" [size]="18" />
          <span>Invest</span>
        </li>
      </ul>
    </section>

    <section class="panel-side">
      <div class="corner"><app-theme-toggle /></div>
      <main class="form-area">
        <nav class="tabs" aria-label="Account">
          <a
            class="tabs__tab"
            routerLink="/auth/register"
            routerLinkActive="tabs__tab--active"
            #register="routerLinkActive"
            [attr.aria-current]="register.isActive ? 'page' : null"
            >Create account</a
          >
          <a
            class="tabs__tab"
            routerLink="/auth/login"
            routerLinkActive="tabs__tab--active"
            #login="routerLinkActive"
            [attr.aria-current]="login.isActive ? 'page' : null"
            >Sign in</a
          >
        </nav>
        <router-outlet />
      </main>
    </section>
  `,
  styleUrl: './auth-layout.scss',
})
export class AuthLayout {
  protected readonly appName = APP_NAME;
}
