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
 * The public /auth calls are left alone: they don't need the token, and a 401
 * there means bad credentials / no refresh cookie, not an expired token.
 * /auth/logout-others is the exception: it needs both the token and the cookie.
 */
const PUBLIC_AUTH = ['register', 'login', 'refresh', 'logout', 'token'];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const baseUrl = inject(API_BASE_URL);
  const store = inject(AuthStore);

  const isPublicAuth = PUBLIC_AUTH.some((path) => req.url === `${baseUrl}/auth/${path}`);
  if (!req.url.startsWith(baseUrl) || isPublicAuth) {
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
