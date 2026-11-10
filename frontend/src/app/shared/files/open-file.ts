import { Observable } from 'rxjs';

/**
 * Opens a stored file in a new tab. The tab opens at once, inside the click, so
 * pop-up blockers allow it; the short-lived signed link arrives a moment later.
 */
export function openInNewTab(link: Observable<{ url: string }>, onError: (e: unknown) => void) {
  const tab = window.open('', '_blank');
  if (tab) tab.opener = null;
  link.subscribe({
    next: ({ url }) => {
      if (tab) tab.location.href = url;
      else window.location.assign(url);
    },
    error: (error: unknown) => {
      tab?.close();
      onError(error);
    },
  });
}

/** Downloads a stored file: its signed link answers with "attachment", so the page stays. */
export function download(link: Observable<{ url: string }>, onError: (e: unknown) => void) {
  link.subscribe({
    next: ({ url }) => window.location.assign(url),
    error: onError,
  });
}

export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
