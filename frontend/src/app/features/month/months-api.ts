import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_BASE_URL } from '../../core/api/api-config';
import {
  AdditionCreate,
  AdditionRead,
  AllocationSet,
  EntryListItem,
  EntryRead,
  IncomeCreate,
  IncomeRead,
  IncomeUpdate,
  MonthCreate,
  MonthRead,
  MonthSummary,
  TransferCreate,
  TransferRead,
} from '../../core/api/types';

/** Months, their incomes and their entries (allocations, additions, transfers). */
@Injectable({ providedIn: 'root' })
export class MonthsApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly months = `${this.base}/months`;

  list(year?: number): Observable<MonthRead[]> {
    const params = year ? new HttpParams().set('year', year) : undefined;
    return this.http.get<MonthRead[]>(this.months, { params });
  }

  /** The user's sheet for a year/month, or null when it was not created yet. */
  find(year: number, month: number): Observable<MonthRead | null> {
    return this.list(year).pipe(map((months) => months.find((m) => m.month === month) ?? null));
  }

  create(body: MonthCreate): Observable<MonthRead> {
    return this.http.post<MonthRead>(this.months, body);
  }

  close(id: string): Observable<MonthRead> {
    return this.http.post<MonthRead>(`${this.months}/${id}/close`, null);
  }

  reopen(id: string): Observable<MonthRead> {
    return this.http.post<MonthRead>(`${this.months}/${id}/reopen`, null);
  }

  summary(id: string): Observable<MonthSummary> {
    return this.http.get<MonthSummary>(`${this.months}/${id}/summary`);
  }

  entries(id: string): Observable<EntryListItem[]> {
    return this.http.get<EntryListItem[]>(`${this.months}/${id}/entries`);
  }

  incomes(id: string): Observable<IncomeRead[]> {
    return this.http.get<IncomeRead[]>(`${this.months}/${id}/incomes`);
  }

  addIncome(id: string, body: IncomeCreate): Observable<IncomeRead> {
    return this.http.post<IncomeRead>(`${this.months}/${id}/incomes`, body);
  }

  updateIncome(incomeId: string, body: IncomeUpdate): Observable<IncomeRead> {
    return this.http.patch<IncomeRead>(`${this.base}/incomes/${incomeId}`, body);
  }

  deleteIncome(incomeId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/incomes/${incomeId}`);
  }

  /** An amount of "0" removes the allocation (the API then answers 204 with no body). */
  setAllocation(id: string, labelId: string, body: AllocationSet): Observable<EntryRead | null> {
    return this.http.put<EntryRead | null>(`${this.months}/${id}/allocations/${labelId}`, body);
  }

  addMoney(id: string, body: AdditionCreate): Observable<AdditionRead> {
    return this.http.post<AdditionRead>(`${this.months}/${id}/additions`, body);
  }

  transfer(id: string, body: TransferCreate): Observable<TransferRead> {
    return this.http.post<TransferRead>(`${this.months}/${id}/transfers`, body);
  }

  deleteEntry(entryId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/entries/${entryId}`);
  }

  restoreEntry(entryId: string): Observable<EntryRead> {
    return this.http.post<EntryRead>(`${this.base}/entries/${entryId}/restore`, null);
  }
}
