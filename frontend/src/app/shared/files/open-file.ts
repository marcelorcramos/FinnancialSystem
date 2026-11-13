import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Opens stored files through their short-lived signed links. A service, so tests
 * replace it instead of the browser's window and location.
 */
@Injectable({ providedIn: 'root' })
export class FileOpener {
  /** In a new tab, opened at once inside the click so pop-up blockers allow it. */
  openInNewTab(link: Observable<{ url: string }>, onError: (e: unknown) => void): void {
    const tab = window.open('', '_blank');
    if (tab) tab.opener = null;
    link.subscribe({
      next: ({ url }) => {
        if (tab) tab.location.href = url;
        else this.go(url);
      },
      error: (error: unknown) => {
        tab?.close();
        onError(error);
      },
    });
  }

  /** As a download: the link answers with "attachment", so the page stays. */
  download(link: Observable<{ url: string }>, onError: (e: unknown) => void): void {
    link.subscribe({ next: ({ url }) => this.go(url), error: onError });
  }

  go(url: string): void {
    window.location.assign(url);
  }
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
