import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { MonthRead } from '../../core/api/types';
import { MonthsApi } from './months-api';

const month = (n: number): MonthRead => ({
  id: `m${n}`,
  year: 2026,
  month: n,
  note: null,
  closed_at: null,
});

describe('MonthsApi', () => {
  let api: MonthsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(MonthsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('finds a month by year and month number', () => {
    let found: MonthRead | null | undefined;
    api.find(2026, 10).subscribe((m) => (found = m));
    http.expectOne('/api/v1/months?year=2026').flush([month(9), month(10)]);
    expect(found?.id).toBe('m10');
  });

  it('returns null when the month does not exist yet', () => {
    let found: MonthRead | null | undefined;
    api.find(2026, 11).subscribe((m) => (found = m));
    http.expectOne('/api/v1/months?year=2026').flush([month(10)]);
    expect(found).toBeNull();
  });

  it('uses the month routes for summary, entries, allocations, additions and transfers', () => {
    api.summary('m10').subscribe();
    api.entries('m10').subscribe();
    api.setAllocation('m10', 'food', { amount: '200.00' }).subscribe();
    api
      .addMoney('m10', { label_id: 'food', amount: '12.00', occurred_on: '2026-10-15' })
      .subscribe();
    api
      .transfer('m10', {
        from_label_id: 'savings',
        to_label_id: 'food',
        amount: '12.00',
        occurred_on: '2026-10-20',
      })
      .subscribe();

    http.expectOne('/api/v1/months/m10/summary').flush({});
    http.expectOne('/api/v1/months/m10/entries').flush([]);
    expect(http.expectOne('/api/v1/months/m10/allocations/food').request.method).toBe('PUT');
    expect(http.expectOne('/api/v1/months/m10/additions').request.method).toBe('POST');
    expect(http.expectOne('/api/v1/months/m10/transfers').request.method).toBe('POST');
  });

  it('deletes and restores entries', () => {
    api.deleteEntry('e1').subscribe();
    api.restoreEntry('e1').subscribe();
    expect(http.expectOne('/api/v1/entries/e1').request.method).toBe('DELETE');
    expect(http.expectOne('/api/v1/entries/e1/restore').request.method).toBe('POST');
  });
});
