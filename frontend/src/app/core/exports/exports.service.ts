import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { filter, map, Observable, switchMap, take, tap, timeout, timer } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import { ExportRead, ReportExportCreate, SignedUrl } from '../api/types';

const POLL_MS = 1000;
const GIVE_UP_MS = 2 * 60 * 1000;

/**
 * Exports are built by the worker: ask for one, poll it until it is ready, then
 * download it through its signed link (the page stays, the file is saved).
 */
@Injectable({ providedIn: 'root' })
export class ExportsService {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  /** True while an export is being prepared, to disable the buttons that ask for one. */
  readonly busy = signal(false);

  report(body: ReportExportCreate): Observable<ExportRead> {
    return this.run(this.http.post<ExportRead>(`${this.api}/exports`, body));
  }

  account(): Observable<ExportRead> {
    return this.run(this.http.post<ExportRead>(`${this.api}/users/me/export`, null));
  }

  get(id: string): Observable<ExportRead> {
    return this.http.get<ExportRead>(`${this.api}/exports/${id}`);
  }

  url(id: string): Observable<SignedUrl> {
    return this.http.get<SignedUrl>(`${this.api}/exports/${id}/url`);
  }

  /** Emits the finished export once its file is downloading; errors if it failed. */
  private run(request: Observable<ExportRead>): Observable<ExportRead> {
    this.busy.set(true);
    return request.pipe(
      switchMap((created) =>
        timer(POLL_MS, POLL_MS).pipe(
          switchMap(() => this.get(created.id)),
          filter((current) => current.status !== 'pending'),
          take(1),
          timeout(GIVE_UP_MS),
        ),
      ),
      switchMap((done) => {
        if (done.status !== 'ready') {
          throw new Error(done.error ?? 'The file could not be prepared. Please try again.');
        }
        return this.url(done.id).pipe(
          tap(({ url }) => window.location.assign(url)),
          map(() => done),
        );
      }),
      tap({ finalize: () => this.busy.set(false) }),
    );
  }
}

/** Message for an export that went wrong. */
export function exportErrorMessage(error: unknown): string {
  if (error instanceof Error && error.name === 'TimeoutError') {
    return 'Preparing the file is taking too long. Please try again later.';
  }
  if (error instanceof Error && !('status' in error)) return error.message;
  return 'Something went wrong. Please try again.';
}
