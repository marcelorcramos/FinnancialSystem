import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';

import { AuthStore, LOGIN_PATH } from './auth-store';

/** Lets authenticated users through, resuming the session from the cookie if needed. */
export const authGuard: CanActivateFn = (_route, state) => {
  const store = inject(AuthStore);
  const router = inject(Router);
  return store
    .restoreSession()
    .pipe(
      map((ok) =>
        ok ? true : router.createUrlTree([LOGIN_PATH], { queryParams: { returnUrl: state.url } }),
      ),
    );
};

/** Keeps signed-in users away from the login and register pages. */
export const guestGuard: CanActivateFn = () => {
  const store = inject(AuthStore);
  const router = inject(Router);
  return store.restoreSession().pipe(map((ok) => (ok ? router.createUrlTree(['/']) : true)));
};

/** Only allows same-app paths as redirect targets after login. */
export function safeReturnUrl(value: string | null | undefined): string {
  if (!value || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/auth')) {
    return '/';
  }
  return value;
}
