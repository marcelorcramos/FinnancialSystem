import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AlertRead } from '../api/types';
import { AuthStore } from '../auth/auth-store';
import { ToastService } from '../../shared/ui/toast.service';
import { alertText, AlertsService } from './alerts.service';

function alert(id: string, level: 'warning' | 'exceeded', seen = false): AlertRead {
  return {
    id,
    level,
    label_id: 'food',
    label_name: 'Food',
    color: '#FFB74D',
    month_id: 'm11',
    year: 2026,
    month: 11,
    limit_amount: '300.00',
    total: level === 'exceeded' ? '320.00' : '250.00',
    seen_at: seen ? '2026-11-03T20:00:00Z' : null,
    created_at: '2026-11-03T20:00:00Z',
  };
}

/** A fetch Response whose body streams the given chunks, then stays open. */
function streaming(chunks: string[]): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
    },
  });
  return new Response(body, { status: 200 });
}

describe('alertText', () => {
  it('says what was reached', () => {
    expect(alertText(alert('a', 'warning'))).toBe(
      'Food reached 80% of its €300.00 limit in November 2026.',
    );
    expect(alertText(alert('b', 'exceeded'))).toBe(
      'Food went over its €300.00 limit in November 2026 (€320.00).',
    );
  });
});

describe('AlertsService', () => {
  let service: AlertsService;
  let http: HttpTestingController;
  let toasts: { show: ReturnType<typeof vi.fn> };
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    toasts = { show: vi.fn() };
    fetchMock = vi.fn(() =>
      Promise.resolve(
        streaming([
          ': connected\n\n',
          `event: alert\ndata: ${JSON.stringify(alert('new', 'exceeded'))}\n\n`,
        ]),
      ),
    );
    vi.stubGlobal('fetch', fetchMock);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthStore, useValue: { accessToken: signal('token-1') } },
        { provide: ToastService, useValue: toasts },
      ],
    });
    service = TestBed.inject(AlertsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    service.stop();
    vi.unstubAllGlobals();
  });

  it('loads the latest alerts and receives new ones live', async () => {
    service.start();
    http.expectOne('/api/v1/alerts').flush([alert('old', 'warning', true)]);
    await vi.waitFor(() => expect(service.alerts().length).toBe(2));

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/alerts/stream',
      expect.objectContaining({ headers: { Authorization: 'Bearer token-1' } }),
    );
    expect(service.alerts().map((a) => a.id)).toEqual(['new', 'old']);
    expect(service.unseen()).toBe(1);
    await vi.waitFor(() =>
      expect(toasts.show).toHaveBeenCalledWith(
        'Food went over its €300.00 limit in November 2026 (€320.00).',
      ),
    );
  });

  it('marks every alert as seen', () => {
    service.start();
    http.expectOne('/api/v1/alerts').flush([alert('a', 'warning'), alert('b', 'exceeded')]);
    service.markAllSeen();
    expect(service.unseen()).toBe(0);
    http.expectOne({ method: 'POST', url: '/api/v1/alerts/seen' }).flush(null);
  });

  it('announces each alert once', () => {
    vi.useFakeTimers();
    service.receive(alert('a', 'warning'));
    service.receive(alert('a', 'warning'));
    vi.advanceTimersByTime(700);
    expect(toasts.show).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('announces a burst of alerts in one toast', () => {
    vi.useFakeTimers();
    // Spread out, each within the wait of the previous one.
    for (const id of ['a', 'b', 'c']) {
      service.receive(alert(id, 'warning'));
      vi.advanceTimersByTime(400);
    }
    expect(toasts.show).not.toHaveBeenCalled();
    vi.advanceTimersByTime(700);
    expect(toasts.show).toHaveBeenCalledTimes(1);
    expect(toasts.show).toHaveBeenCalledWith('3 new alerts. Open the bell to see them.');
    expect(service.unseen()).toBe(3);
    vi.useRealTimers();
  });

  it('does not hold alerts back for ever during a long stream', () => {
    vi.useFakeTimers();
    for (let i = 0; i < 10; i++) {
      service.receive(alert(`x${i}`, 'warning'));
      vi.advanceTimersByTime(500);
    }
    expect(toasts.show).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
