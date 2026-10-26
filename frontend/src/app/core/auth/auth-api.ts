import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import { LoginRequest, RegisterRequest, TokenResponse, UserRead } from './auth.models';

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

  login(body: LoginRequest): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/login`, body, {
      withCredentials: true,
    });
  }

  refresh(): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${this.baseUrl}/auth/refresh`, null, {
      withCredentials: true,
    });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/auth/logout`, null, { withCredentials: true });
  }

  me(): Observable<UserRead> {
    return this.http.get<UserRead>(`${this.baseUrl}/users/me`);
  }
}
