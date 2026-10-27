import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { LabelsApi } from './labels-api';

describe('LabelsApi', () => {
  let api: LabelsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(LabelsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists labels, optionally with archived ones', () => {
    api.list(true).subscribe();
    const req = http.expectOne('/api/v1/labels?include_archived=true');
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('returns only the colors of the suggestions', () => {
    let colors: string[] = [];
    api.colorSuggestions().subscribe((c) => (colors = c));
    http.expectOne('/api/v1/labels/color-suggestions').flush({ colors: ['#EF5350'] });
    expect(colors).toEqual(['#EF5350']);
  });

  it('deletes with or without reassignment', () => {
    api.delete('a').subscribe();
    http.expectOne('/api/v1/labels/a').flush(null);

    api.delete('a', 'b').subscribe();
    const req = http.expectOne('/api/v1/labels/a?reassign_to=b');
    expect(req.request.method).toBe('DELETE');
    req.flush(null);
  });

  it('archives, unarchives and restores', () => {
    api.archive('a').subscribe();
    api.unarchive('a').subscribe();
    api.restore('a').subscribe();
    for (const action of ['archive', 'unarchive', 'restore']) {
      const req = http.expectOne(`/api/v1/labels/a/${action}`);
      expect(req.request.method).toBe('POST');
      req.flush({});
    }
  });
});
