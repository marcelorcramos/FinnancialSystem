import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import { AttachmentRead, SignedUrl } from '../../core/api/types';

/** Accepted like the API: checked here first so the user hears about it at once. */
export const RECEIPT_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
export const RECEIPT_MAX_BYTES = 10 * 1024 * 1024;

/** Problem with a file before uploading it, or null when it can go. */
export function receiptProblem(file: File): string | null {
  if (!RECEIPT_TYPES.includes(file.type)) {
    return `${file.name}: only JPEG, PNG, WebP images and PDF files are accepted`;
  }
  if (file.size > RECEIPT_MAX_BYTES) return `${file.name} is larger than 10 MB`;
  if (file.size === 0) return `${file.name} is empty`;
  return null;
}

/** Receipts (photos and PDFs) of a month or one of its entries. */
@Injectable({ providedIn: 'root' })
export class ReceiptsApi {
  private readonly http = inject(HttpClient);
  private readonly api = inject(API_BASE_URL);

  list(monthId: string): Observable<AttachmentRead[]> {
    return this.http.get<AttachmentRead[]>(`${this.api}/months/${monthId}/attachments`);
  }

  upload(monthId: string, file: File, entryId: string | null): Observable<AttachmentRead> {
    const body = new FormData();
    body.append('file', file, file.name);
    if (entryId) body.append('entry_id', entryId);
    return this.http.post<AttachmentRead>(`${this.api}/months/${monthId}/attachments`, body);
  }

  url(id: string, download = false): Observable<SignedUrl> {
    return this.http.get<SignedUrl>(`${this.api}/attachments/${id}/url`, {
      params: download ? { download: true } : {},
    });
  }

  remove(id: string): Observable<void> {
    return this.http.delete<void>(`${this.api}/attachments/${id}`);
  }

  restore(id: string): Observable<AttachmentRead> {
    return this.http.post<AttachmentRead>(`${this.api}/attachments/${id}/restore`, null);
  }
}
