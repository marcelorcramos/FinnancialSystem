import { Subject } from 'rxjs';

import { withCrossTabLock } from './cross-tab-lock';

/** In-memory stand-in for navigator.locks: one holder per name, others queue. */
class FakeLocks {
  private queue = Promise.resolve();

  request(_name: string, callback: () => Promise<void>): Promise<void> {
    const run = this.queue.then(callback);
    this.queue = run.catch(() => undefined);
    return run;
  }
}

describe('withCrossTabLock', () => {
  const original = Object.getOwnPropertyDescriptor(navigator, 'locks');

  beforeEach(() => {
    Object.defineProperty(navigator, 'locks', { value: new FakeLocks(), configurable: true });
  });

  afterEach(() => {
    if (original) {
      Object.defineProperty(navigator, 'locks', original);
    } else {
      delete (navigator as { locks?: unknown }).locks;
    }
  });

  const flush = () => new Promise((resolve) => setTimeout(resolve));

  it('runs one holder at a time', async () => {
    const first = new Subject<string>();
    const second = new Subject<string>();
    const log: string[] = [];

    withCrossTabLock('refresh', first).subscribe((v) => log.push(v));
    withCrossTabLock('refresh', second).subscribe((v) => log.push(v));
    await flush();

    second.next('second (too early)');
    first.next('first');
    first.complete();
    await flush();
    second.next('second');
    second.complete();

    expect(log).toEqual(['first', 'second']);
  });

  it('releases the lock when the source fails', async () => {
    const failing = new Subject<string>();
    const next = new Subject<string>();
    const errors: unknown[] = [];
    const values: string[] = [];

    withCrossTabLock('refresh', failing).subscribe({ error: (e) => errors.push(e) });
    withCrossTabLock('refresh', next).subscribe((v) => values.push(v));
    await flush();
    failing.error('boom');
    await flush();
    next.next('ok');

    expect(errors).toEqual(['boom']);
    expect(values).toEqual(['ok']);
  });
});
