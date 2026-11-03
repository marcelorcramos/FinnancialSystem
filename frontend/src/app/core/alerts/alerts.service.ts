import { HttpClient } from '@angular/common/http';
import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { API_BASE_URL } from '../api/api-config';
import { AlertRead } from '../api/types';
import { AuthStore } from '../auth/auth-store';
import { formatMoney } from '../../shared/money/format-money';
import { ToastService } from '../../shared/ui/toast.service';
import { SseParser } from './sse';

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const MAX_RETRY_MS = 30_000;

/** "Food reached 80% of its €300.00 limit in November 2026." */
export function alertText(alert: AlertRead): string {
  const month = `${MONTHS[alert.month - 1]} ${alert.year}`;
  const limit = formatMoney(alert.limit_amount);
  return alert.level === 'exceeded'
    ? `${alert.label_name} went over its ${limit} limit in ${month} (${formatMoney(alert.total)}).`
    : `${alert.label_name} reached 80% of its ${limit} limit in ${month}.`;
}

/**
 * Limit alerts: the latest ones from the API and new ones as they are raised, over
 * Server-Sent Events. The stream is read with fetch because it needs the Bearer
 * header; it reconnects with a growing pause and refreshes the token on a 401.
 */
@Injectable({ providedIn: 'root' })
export class AlertsService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthStore);
  private readonly toasts = inject(ToastService);
  private readonly url = `${inject(API_BASE_URL)}/alerts`;

  private readonly _alerts = signal<AlertRead[]>([]);
  readonly alerts = this._alerts.asReadonly();
  readonly unseen = computed(() => this._alerts().filter((a) => !a.seen_at).length);

  private controller: AbortController | null = null;
  private retryMs = 1000;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    inject(DestroyRef).onDestroy(() => this.stop());
  }

  /** Loads the latest alerts and listens for new ones until stop(). */
  start(): void {
    if (this.controller) return;
    this.controller = new AbortController();
    this.http.get<AlertRead[]>(this.url).subscribe({ next: (list) => this._alerts.set(list) });
    void this.listen(this.controller);
  }

  stop(): void {
    this.controller?.abort();
    this.controller = null;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.retryTimer = null;
    this._alerts.set([]);
  }

  markAllSeen(): void {
    if (!this.unseen()) return;
    const now = new Date().toISOString();
    this._alerts.update((list) => list.map((a) => ({ ...a, seen_at: a.seen_at ?? now })));
    this.http.post<void>(`${this.url}/seen`, null).subscribe();
  }

  /** A new alert from the stream: listed first and announced once. */
  receive(alert: AlertRead): void {
    if (this._alerts().some((a) => a.id === alert.id)) return;
    this._alerts.update((list) => [alert, ...list].slice(0, 50));
    this.toasts.show(alertText(alert));
  }

  private async listen(controller: AbortController): Promise<void> {
    try {
      const response = await fetch(`${this.url}/stream`, {
        headers: { Authorization: `Bearer ${this.auth.accessToken() ?? ''}` },
        signal: controller.signal,
      });
      if (response.status === 401) {
        await firstValueFrom(this.auth.refresh());
        return this.reconnect(controller, 0);
      }
      if (!response.ok || !response.body) throw new Error(`stream ${response.status}`);
      this.retryMs = 1000;
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      const parser = new SseParser();
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        for (const event of parser.push(value)) {
          if (event.event === 'alert') this.receive(JSON.parse(event.data) as AlertRead);
        }
      }
    } catch {
      if (controller.signal.aborted) return;
    }
    this.reconnect(controller, this.retryMs);
    this.retryMs = Math.min(this.retryMs * 2, MAX_RETRY_MS);
  }

  private reconnect(controller: AbortController, delay: number): void {
    if (controller.signal.aborted || controller !== this.controller) return;
    this.retryTimer = setTimeout(() => void this.listen(controller), delay);
  }
}
