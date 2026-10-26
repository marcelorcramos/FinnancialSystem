import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import { AuthStore } from './auth-store';

function withBearer<T>(req: HttpRequest<T>, token: string | null): HttpRequest<T> {
  return token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;
}

/**
 * Sends the access token to the API and, when a request fails with 401,
 * refreshes the token once and retries. If the refresh fails the session is
 * expired and the user is sent to the login page.
 *
 * /auth/* calls are left alone: they either don't need the token or a 401
 * there means bad credentials / no refresh cookie, not an expired token.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const baseUrl = inject(API_BASE_URL);
  const store = inject(AuthStore);

  if (!req.url.startsWith(baseUrl) || req.url.startsWith(`${baseUrl}/auth/`)) {
    return next(req);
  }

  return next(withBearer(req, store.accessToken())).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401) {
        return throwError(() => error);
      }
      return store.refresh().pipe(
        catchError(() => {
          store.expireSession();
          return throwError(() => error);
        }),
        switchMap((token) => next(withBearer(req, token))),
      );
    }),
  );
};
