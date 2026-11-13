import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { FileOpener } from '../../shared/files/open-file';
import { API } from '../auth/testing';
import { ExportRead } from '../api/types';
import { exportErrorMessage, ExportsService } from './exports.service';

const PENDING: ExportRead = {
  id: 'x1',
  kind: 'report',
  format: 'csv',
  status: 'pending',
  period: 'last_month',
  label_ids: [],
  kinds: [],
  reference_date: '2026-11-10',
  filename: null,
  size: null,
  error: null,
  created_at: '2026-11-10T10:00:00Z',
  completed_at: null,
  expires_at: null,
};

describe('ExportsService', () => {
  let service: ExportsService;
  let http: HttpTestingController;
  let assign: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.useFakeTimers();
    assign = vi.fn();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: FileOpener, useValue: { go: assign } },
      ],
    });
    service = TestBed.inject(ExportsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    vi.useRealTimers();
  });

  it('asks for the export, polls until it is ready and downloads it', () => {
    let done: ExportRead | undefined;
    service.report({ format: 'csv', period: 'last_month' }).subscribe((e) => (done = e));
    expect(service.busy()).toBe(true);

    const create = http.expectOne(`${API}/exports`);
    expect(create.request.body).toEqual({ format: 'csv', period: 'last_month' });
    create.flush(PENDING);

    vi.advanceTimersByTime(1000);
    http.expectOne(`${API}/exports/x1`).flush(PENDING);
    vi.advanceTimersByTime(1000);
    const ready = { ...PENDING, status: 'ready' as const, filename: 'r.csv' };
    http.expectOne(`${API}/exports/x1`).flush(ready);
    http.expectOne(`${API}/exports/x1/url`).flush({ url: 'https://s3/r.csv', expires_in: 300 });

    expect(assign).toHaveBeenCalledWith('https://s3/r.csv');
    expect(done?.filename).toBe('r.csv');
    expect(service.busy()).toBe(false);
  });

  it('reports an export that failed', () => {
    let error: unknown;
    service.account().subscribe({ error: (e: unknown) => (error = e) });
    http.expectOne(`${API}/users/me/export`).flush({ ...PENDING, kind: 'account' });
    vi.advanceTimersByTime(1000);
    http
      .expectOne(`${API}/exports/x1`)
      .flush({ ...PENDING, status: 'failed', error: 'The file could not be built (X)' });
    expect(exportErrorMessage(error)).toBe('The file could not be built (X)');
    expect(assign).not.toHaveBeenCalled();
    expect(service.busy()).toBe(false);
  });
});
