import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-errors';
import { APP_NAME } from '../../core/app-title-strategy';
import { AuthStore } from '../../core/auth/auth-store';
import { ThemeToggle } from '../../core/layout/theme-toggle';
import { Icon } from '../../shared/ui/icon';
import { ToastOutlet } from '../../shared/ui/toast-outlet';
import { ToastService } from '../../shared/ui/toast.service';

@Component({
  selector: 'app-auth-layout',
  imports: [Icon, RouterLink, RouterLinkActive, RouterOutlet, ThemeToggle, ToastOutlet],
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
      <div class="try">
        <button
          type="button"
          class="btn btn--primary"
          [disabled]="startingDemo()"
          (click)="tryDemo()"
        >
          @if (startingDemo()) {
            <span class="spinner" aria-hidden="true"></span> Preparing your demo…
          } @else {
            Try it with sample data
          }
        </button>
        <span class="try__hint">No sign-up: six months of example money, yours for 24 hours.</span>
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
    <!-- Messages that follow the user here (password changed, account deleted). -->
    <app-toast-outlet />
  `,
  styleUrl: './auth-layout.scss',
})
export class AuthLayout {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly toasts = inject(ToastService);

  protected readonly appName = APP_NAME;
  protected readonly startingDemo = signal(false);

  /** A fresh demo account of its own, then straight into the app. */
  protected tryDemo(): void {
    this.startingDemo.set(true);
    this.auth.startDemo().subscribe({
      next: () => void this.router.navigateByUrl('/'),
      error: (error: unknown) => {
        this.startingDemo.set(false);
        this.toasts.show(apiErrorMessage(error));
      },
    });
  }
}
