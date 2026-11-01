import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import {
  catchError,
  finalize,
  map,
  Observable,
  of,
  shareReplay,
  switchMap,
  tap,
  throwError,
} from 'rxjs';

import { AuthApi } from './auth-api';
import { withCrossTabLock } from './cross-tab-lock';
import { LoginRequest, ProfileUpdate, RegisterRequest, UserRead } from './auth.models';

export const LOGIN_PATH = '/auth/login';
const REFRESH_LOCK = 'finnancial.auth.refresh';

/**
 * Session state. The access token lives only in memory; after a reload the
 * session is restored through the HttpOnly refresh cookie.
 */
@Injectable({ providedIn: 'root' })
export class AuthStore {
  private readonly api = inject(AuthApi);
  private readonly router = inject(Router);

  private readonly _accessToken = signal<string | null>(null);
  private readonly _user = signal<UserRead | null>(null);
  private readonly _sessionExpired = signal(false);

  readonly accessToken = this._accessToken.asReadonly();
  readonly user = this._user.asReadonly();
  readonly isAuthenticated = computed(() => this._accessToken() !== null);
  /** True after a session was lost (refresh failed), until the next login. */
  readonly sessionExpired = this._sessionExpired.asReadonly();

  private refreshInFlight: Observable<string> | null = null;
  private restoreAttempt: Observable<boolean> | null = null;

  login(credentials: LoginRequest): Observable<UserRead> {
    return this.api.login(credentials).pipe(
      tap((tokens) => {
        this._accessToken.set(tokens.access_token);
        this._sessionExpired.set(false);
      }),
      switchMap(() => this.loadUser()),
    );
  }

  /** Registers and signs in with the same credentials. */
  register(data: RegisterRequest): Observable<UserRead> {
    return this.api
      .register(data)
      .pipe(switchMap(() => this.login({ email: data.email, password: data.password })));
  }

  /**
   * Gets a new access token from the refresh cookie. Concurrent callers (e.g.
   * several requests failing with 401 at once) share a single request, and
   * other tabs wait for it, since the backend rotates the refresh token and
   * reusing it revokes the family.
   */
  refresh(): Observable<string> {
    this.refreshInFlight ??= withCrossTabLock(REFRESH_LOCK, this.api.refresh()).pipe(
      map((tokens) => tokens.access_token),
      tap((token) => this._accessToken.set(token)),
      catchError((error: unknown) => {
        this.clearSession({ expired: this.isAuthenticated() });
        return throwError(() => error);
      }),
      finalize(() => (this.refreshInFlight = null)),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.refreshInFlight;
  }

  /**
   * Tries once per app load to resume a session from the refresh cookie.
   * Emits whether the user is authenticated afterwards.
   */
  restoreSession(): Observable<boolean> {
    if (this.isAuthenticated()) {
      return of(true);
    }
    this.restoreAttempt ??= this.refresh().pipe(
      switchMap(() => this.loadUser()),
      map(() => true),
      catchError(() => of(false)),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    return this.restoreAttempt;
  }

  logout(): Observable<void> {
    return this.api.logout().pipe(
      catchError(() => of(undefined)),
      map(() => undefined),
      finalize(() => {
        this.clearSession();
        void this.router.navigateByUrl(LOGIN_PATH);
      }),
    );
  }

  updateProfile(changes: ProfileUpdate): Observable<UserRead> {
    return this.api.updateMe(changes).pipe(tap((user) => this._user.set(user)));
  }

  /**
   * Changes the password. The API ends every session, so this one signs in
   * again with the new password and only the other devices are signed out.
   */
  changePassword(currentPassword: string, newPassword: string): Observable<UserRead> {
    const email = this._user()?.email;
    if (!email) return throwError(() => new Error('Not signed in'));
    return this.api
      .changePassword(currentPassword, newPassword)
      .pipe(switchMap(() => this.login({ email, password: newPassword })));
  }

  logoutOthers(): Observable<void> {
    return this.api.logoutOthers();
  }

  /** Called when the API rejects us and the refresh cookie no longer works. */
  expireSession(): void {
    this.clearSession({ expired: this.isAuthenticated() || this.sessionExpired() });
    const returnUrl = this.router.url;
    void this.router.navigate([LOGIN_PATH], {
      queryParams: returnUrl && !returnUrl.startsWith('/auth') ? { returnUrl } : {},
    });
  }

  private loadUser(): Observable<UserRead> {
    return this.api.me().pipe(tap((user) => this._user.set(user)));
  }

  private clearSession(options: { expired?: boolean } = {}): void {
    this._accessToken.set(null);
    this._user.set(null);
    this._sessionExpired.set(options.expired ?? false);
    // We know there is no usable refresh cookie now: don't try to restore.
    this.restoreAttempt = of(false);
  }
}
