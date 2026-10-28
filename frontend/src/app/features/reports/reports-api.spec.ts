import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_BASE_URL } from '../../core/api/api-config';
import { ReportsApi } from './reports-api';

describe('ReportsApi', () => {
  let api: ReportsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: '/api/v1' },
      ],
    });
    api = TestBed.inject(ReportsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends the period and repeats label_ids and kinds', () => {
    api
      .series({ period: 'last_6_months', labelIds: ['a', 'b'], kinds: ['investment'] })
      .subscribe();
    const request = http.expectOne((r) => r.url === '/api/v1/reports/series');
    expect(request.request.params.get('period')).toBe('last_6_months');
    expect(request.request.params.getAll('label_ids')).toEqual(['a', 'b']);
    expect(request.request.params.getAll('kinds')).toEqual(['investment']);
    request.flush({});
  });

  it('asks for every label and all time without filters', () => {
    api.summary().subscribe();
    const request = http.expectOne('/api/v1/reports/summary');
    expect(request.request.params.keys()).toEqual([]);
    request.flush({});
  });
});
