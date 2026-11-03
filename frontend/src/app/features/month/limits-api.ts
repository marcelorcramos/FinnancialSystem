import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import { LimitRead, LimitStatus } from '../../core/api/types';

/** Limits per label: a default for every month, or one for a single month. */
@Injectable({ providedIn: 'root' })
export class LimitsApi {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  status(monthId: string): Observable<LimitStatus[]> {
    return this.http.get<LimitStatus[]>(`${this.api}/months/${monthId}/limits`);
  }

  list(): Observable<LimitRead[]> {
    return this.http.get<LimitRead[]>(`${this.api}/limits`);
  }

  /** `monthId` null sets the label's default limit. */
  set(labelId: string, amount: string, monthId: string | null): Observable<LimitRead> {
    const url = monthId
      ? `${this.api}/months/${monthId}/limits/${labelId}`
      : `${this.api}/labels/${labelId}/limit`;
    return this.http.put<LimitRead>(url, { amount });
  }

  remove(labelId: string, monthId: string | null): Observable<void> {
    const url = monthId
      ? `${this.api}/months/${monthId}/limits/${labelId}`
      : `${this.api}/labels/${labelId}/limit`;
    return this.http.delete<void>(url);
  }
}
