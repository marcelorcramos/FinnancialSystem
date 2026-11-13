import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthStore, LOGIN_PATH } from '../../../core/auth/auth-store';

/**
 * Where Google sends the browser back after a successful sign-in: the API has
 * set the refresh cookie, so the session is picked up from it.
 */
@Component({
  selector: 'app-google-done-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <p class="status" role="status">
      <span class="spinner" aria-hidden="true"></span> Signing you in…
    </p>
  `,
  styles: `
    .status {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      margin: 0;
    }
  `,
})
export default class GoogleDonePage {
  constructor() {
    const auth = inject(AuthStore);
    const router = inject(Router);
    auth.restoreSession().subscribe((signedIn) => {
      void router.navigateByUrl(
        signedIn ? '/' : router.createUrlTree([LOGIN_PATH], { queryParams: { error: 'google' } }),
      );
    });
  }
}
