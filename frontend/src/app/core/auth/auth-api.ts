import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import {
  LoginRequest,
  ProfileUpdate,
  RegisterRequest,
  TokenResponse,
  TwoFactorRequired,
  UserRead,
} from './auth.models';

/**
 * Thin HTTP client for /auth and /users/me. Calls that set or read the
 * refresh_token cookie (Path=/api/v1/auth) go with credentials.
 */
@Injectable({ providedIn: 'root' })
export class AuthApi {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  register(body: RegisterRequest): Observable<UserRead> {
    return this.http.post<UserRead>(`${this.baseUrl}/auth/register`, body);
  }

  /** Tokens, or a ticket when the account has two-factor sign-in on. */
  login(body: LoginRequest): Observable<TokenResponse | TwoFactorRequired> {
    return this.http.post<TokenResponse | TwoFactorRequired>(`${this.baseUrl}/auth/login`, body, {
      withCredentials: true,
    });
  }

  loginTwoFactor(ticket: string, code: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(
      `${this.baseUrl}/auth/login/2fa`,
      { ticket, code },
      { withCredentials: true },
    );
  }

  /** A new demo account, signed in (refresh cookie set). */
  demo(): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/demo`, null, {
      withCredentials: true,
    });
  }

  providers(): Observable<{ google: boolean }> {
    return this.http.get<{ google: boolean }>(`${this.baseUrl}/auth/providers`);
  }

  refresh(): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/refresh`, null, {
      withCredentials: true,
    });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/logout`, null, { withCredentials: true });
  }

  /** Ends every other session; the refresh cookie tells the API which one to keep. */
  logoutOthers(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/logout-others`, null, {
      withCredentials: true,
    });
  }

  me(): Observable<UserRead> {
    return this.http.get<UserRead>(`${this.baseUrl}/users/me`);
  }

  updateMe(body: ProfileUpdate): Observable<UserRead> {
    return this.http.patch<UserRead>(`${this.baseUrl}/users/me`, body);
  }

  /** Emails a reset link; the API answers the same whether the email has an account. */
  requestPasswordReset(email: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/password-reset`, { email });
  }

  /** Sets a new password with the emailed token; every session ends. */
  resetPassword(token: string, newPassword: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/password-reset/confirm`, {
      token,
      new_password: newPassword,
    });
  }

  verifyEmail(token: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/verify-email`, { token });
  }

  resendVerification(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/users/me/verification-email`, null);
  }

  /**
   * Deletes the account and all of its data for good; clears the refresh cookie.
   * Accounts without a password confirm with their email instead.
   */
  deleteAccount(confirmation: { password: string } | { confirm_email: string }): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/users/me`, {
      body: confirmation,
      withCredentials: true,
    });
  }

  /** Ends every session, this one included (see AuthStore.changePassword). */
  changePassword(currentPassword: string, newPassword: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/users/me/password`, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }
}
