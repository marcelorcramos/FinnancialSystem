import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import { ColorSuggestions, LabelCreate, LabelRead, LabelUpdate } from '../../core/api/types';

@Injectable({ providedIn: 'root' })
export class LabelsApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/labels`;

  list(includeArchived = false): Observable<LabelRead[]> {
    const params = new HttpParams().set('include_archived', includeArchived);
    return this.http.get<LabelRead[]>(this.url, { params });
  }

  colorSuggestions(): Observable<string[]> {
    return this.http
      .get<ColorSuggestions>(`${this.url}/color-suggestions`)
      .pipe(map((body) => body.colors));
  }

  create(body: LabelCreate): Observable<LabelRead> {
    return this.http.post<LabelRead>(this.url, body);
  }

  update(id: string, body: LabelUpdate): Observable<LabelRead> {
    return this.http.patch<LabelRead>(`${this.url}/${id}`, body);
  }

  archive(id: string): Observable<LabelRead> {
    return this.http.post<LabelRead>(`${this.url}/${id}/archive`, null);
  }

  unarchive(id: string): Observable<LabelRead> {
    return this.http.post<LabelRead>(`${this.url}/${id}/unarchive`, null);
  }

  /** `reassignTo` is required by the API when the label has entries. */
  delete(id: string, reassignTo?: string): Observable<void> {
    const params = reassignTo ? new HttpParams().set('reassign_to', reassignTo) : undefined;
    return this.http.delete<void>(`${this.url}/${id}`, { params });
  }

  restore(id: string): Observable<LabelRead> {
    return this.http.post<LabelRead>(`${this.url}/${id}/restore`, null);
  }
}
