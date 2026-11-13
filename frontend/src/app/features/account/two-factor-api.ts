import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import { RecoveryCodes, TwoFactorSetup, TwoFactorStatus } from '../../core/api/types';

/** Two-factor sign-in of the signed-in user (TOTP and recovery codes). */
@Injectable({ providedIn: 'root' })
export class TwoFactorApi {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  status(): Observable<TwoFactorStatus> {
    return this.http.get<TwoFactorStatus>(`${this.api}/users/me/2fa`);
  }

  setup(): Observable<TwoFactorSetup> {
    return this.http.post<TwoFactorSetup>(`${this.api}/users/me/2fa/setup`, null);
  }

  enable(code: string): Observable<RecoveryCodes> {
    return this.http.post<RecoveryCodes>(`${this.api}/users/me/2fa/enable`, { code });
  }

  disable(code: string): Observable<void> {
    return this.http.post<void>(`${this.api}/users/me/2fa/disable`, { code });
  }

  recoveryCodes(code: string): Observable<RecoveryCodes> {
    return this.http.post<RecoveryCodes>(`${this.api}/users/me/2fa/recovery-codes`, { code });
  }
}
