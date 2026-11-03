import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import { GoalCreate, GoalList, GoalRead, GoalUpdate } from '../../core/api/types';

@Injectable({ providedIn: 'root' })
export class GoalsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/goals`;

  list(): Observable<GoalList> {
    return this.http.get<GoalList>(this.url);
  }

  create(body: GoalCreate): Observable<GoalRead> {
    return this.http.post<GoalRead>(this.url, body);
  }

  update(id: string, body: GoalUpdate): Observable<GoalRead> {
    return this.http.patch<GoalRead>(`${this.url}/${id}`, body);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`);
  }

  restore(id: string): Observable<GoalRead> {
    return this.http.post<GoalRead>(`${this.url}/${id}/restore`, null);
  }
}
