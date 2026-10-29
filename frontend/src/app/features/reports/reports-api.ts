import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import {
  LabelKind,
  ReportEntries,
  ReportPeriod,
  ReportSeries,
  ReportSummary,
} from '../../core/api/types';

/** Report filters: a rolling time window and any mix of labels and kinds (a union). */
export interface ReportFilter {
  period?: ReportPeriod;
  labelIds?: readonly string[];
  kinds?: readonly LabelKind[];
}

/** Reports by period and category: totals (donut), series (line chart) and entries. */
@Injectable({ providedIn: 'root' })
export class ReportsApi {
  private readonly http = inject(HttpClient);
  private readonly reports = `${inject(API_BASE_URL)}/reports`;

  summary(filter: ReportFilter = {}): Observable<ReportSummary> {
    return this.http.get<ReportSummary>(`${this.reports}/summary`, { params: params(filter) });
  }

  series(filter: ReportFilter = {}): Observable<ReportSeries> {
    return this.http.get<ReportSeries>(`${this.reports}/series`, { params: params(filter) });
  }

  /** One page of the entries behind the totals, newest first. */
  entries(filter: ReportFilter = {}, page = { limit: 50, offset: 0 }): Observable<ReportEntries> {
    const query = params(filter).set('limit', page.limit).set('offset', page.offset);
    return this.http.get<ReportEntries>(`${this.reports}/entries`, { params: query });
  }
}

function params({ period, labelIds = [], kinds = [] }: ReportFilter): HttpParams {
  let result = new HttpParams();
  if (period) result = result.set('period', period);
  for (const id of labelIds) result = result.append('label_ids', id);
  for (const kind of kinds) result = result.append('kinds', kind);
  return result;
}
