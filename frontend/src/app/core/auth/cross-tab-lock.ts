import { Observable } from 'rxjs';

/**
 * Runs `source` while holding a lock shared by every tab of the app (Web Locks
 * API), so only one tab at a time does it. Used for the token refresh: the
 * backend rotates the refresh cookie and treats a reused one as theft, so two
 * tabs refreshing at once (e.g. both reloading) would revoke the session. The
 * second tab waits and then sends the cookie the first one just received.
 *
 * Falls back to running `source` directly where the API is not available.
 */
export function withCrossTabLock<T>(name: string, source: Observable<T>): Observable<T> {
  const locks = globalThis.navigator?.locks;
  if (!locks) return source;

  return new Observable<T>((subscriber) => {
    let release: (() => void) | undefined;
    let stopped = false;

    locks
      .request(
        name,
        () =>
          new Promise<void>((resolve) => {
            release = resolve;
            if (stopped) {
              resolve();
              return;
            }
            source.subscribe({
              next: (value) => subscriber.next(value),
              error: (error: unknown) => {
                resolve();
                subscriber.error(error);
              },
              complete: () => {
                resolve();
                subscriber.complete();
              },
            });
          }),
      )
      .catch((error: unknown) => subscriber.error(error));

    return () => {
      stopped = true;
      release?.();
    };
  });
}
