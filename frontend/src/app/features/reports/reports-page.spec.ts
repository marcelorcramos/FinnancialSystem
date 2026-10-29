import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { LabelRead, ReportSeries } from '../../core/api/types';
import { LabelsApi } from '../labels/labels-api';
import { ReportsApi } from './reports-api';
import ReportsPage from './reports-page';
import { reportEntry, SUMMARY } from './testing';

function label(id: string, name: string, archived = false): LabelRead {
  return {
    id,
    name,
    kind: 'expense',
    color: '#FFB74D',
    icon: 'restaurant',
    is_default: false,
    archived_at: archived ? '2026-09-01T00:00:00Z' : null,
    created_at: '2026-01-01T00:00:00Z',
  } as LabelRead;
}

const SERIES = {
  months: ['2026-09', '2026-10'],
  totals: [
    { month: '2026-09', total: '300.00' },
    { month: '2026-10', total: '500.00' },
  ],
  labels: [],
} as unknown as ReportSeries;

describe('ReportsPage', () => {
  let fixture: ComponentFixture<ReportsPage>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let navigate: ReturnType<typeof vi.spyOn>;

  async function render(params: Record<string, string | string[]> = {}) {
    api = {
      summary: vi.fn(() => of(SUMMARY)),
      series: vi.fn(() => of(SERIES)),
      entries: vi.fn(() =>
        of({ count: 3, entries: [reportEntry({ id: 'e1' }), reportEntry({ id: 'e2' })] }),
      ),
    };
    TestBed.configureTestingModule({
      imports: [ReportsPage],
      providers: [
        provideRouter([]),
        { provide: ReportsApi, useValue: api },
        {
          provide: LabelsApi,
          useValue: {
            list: vi.fn(() =>
              of([label('food', 'Food'), label('savings', 'Savings'), label('gym', 'Gym', true)]),
            ),
          },
        },
      ],
    });
    navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    fixture = TestBed.createComponent(ReportsPage);
    for (const [name, value] of Object.entries(params)) fixture.componentRef.setInput(name, value);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const text = (selector: string) =>
    [...el.querySelectorAll(selector)].map((e) => e.textContent?.replace(/\s+/g, ' ').trim());
  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find((b) =>
      b.textContent?.replace(/\s+/g, ' ').includes(name),
    )!;

  it('shows the last 6 months of every label by default', async () => {
    await render();
    expect(api['summary']).toHaveBeenCalledWith({
      period: 'last_6_months',
      kinds: [],
      labelIds: [],
    });
    expect(button('Last 6 months').getAttribute('aria-pressed')).toBe('true');
    expect(text('.total__value')).toEqual(['€500.00', '€212.00', '€288.00', '€0.00']);
    expect(text('.total__hint')).toEqual(['May 2026 – Oct 2026']);
    expect(text('.bar__name')).toEqual(['Savings', 'Food']);
    expect(text('.bars__empty')).toEqual(['1 selected label has no money in this period.']);
    expect(text('.trend__stats dd')).toEqual(['€400.00', '€500.00']);
    expect(text('.entries__head .muted')).toEqual(['3 in May 2026 – Oct 2026']);
    // Archived labels are not offered unless already chosen.
    expect(text('.chips[aria-label=Labels] .chip')).toEqual(['Food', 'Savings']);
  });

  it('reads the filters from the URL', async () => {
    await render({ period: 'all', kind: 'saving', label: ['food', 'gym'] });
    expect(api['summary']).toHaveBeenCalledWith({
      period: 'all',
      kinds: ['saving'],
      labelIds: ['food', 'gym'],
    });
    expect(api['entries']).toHaveBeenCalledWith(
      { period: 'all', kinds: ['saving'], labelIds: ['food', 'gym'] },
      { limit: 50, offset: 0 },
    );
    const pressed = text('.chip[aria-pressed=true]');
    expect(pressed).toEqual(['Saving', 'Food', 'Gym']);
    expect(el.textContent).toContain('Showing the selected kinds and labels together');
  });

  it('writes the filters to the URL, leaving out the default period', async () => {
    await render({ label: 'food' });
    button('Investment').click();
    expect(navigate).toHaveBeenLastCalledWith(
      [],
      expect.objectContaining({
        queryParams: { kind: ['investment'] },
        queryParamsHandling: 'merge',
      }),
    );
    button('Food').click();
    expect(navigate.mock.lastCall![1].queryParams).toEqual({ label: null });
    button('All time').click();
    expect(navigate.mock.lastCall![1].queryParams).toEqual({ period: 'all' });
    button('Last 6 months').click();
    expect(navigate.mock.lastCall![1].queryParams).toEqual({ period: null });
    button('Clear').click();
    expect(navigate.mock.lastCall![1].queryParams).toEqual({ kind: null, label: null });
  });

  it('shows the labels as a table too', async () => {
    await render();
    button('Table').click();
    await fixture.whenStable();
    const cells = [...el.querySelectorAll('tbody tr')].map((row) =>
      [...row.children].map((cell) => cell.textContent?.trim()),
    );
    expect(cells).toEqual([
      ['Savings', '€300.00', '€0.00', '€0.00', '−€12.00', '€288.00', '57.6%'],
      ['Food', '€150.00', '€50.00', '€12.00', '€0.00', '€212.00', '42.4%'],
    ]);
  });

  it('loads more entries after the first page', async () => {
    await render();
    expect(text('.entry')).toHaveLength(2);
    api['entries']!.mockReturnValueOnce(of({ count: 3, entries: [reportEntry({ id: 'e3' })] }));
    button('Show more').click();
    await fixture.whenStable();
    expect(api['entries']).toHaveBeenLastCalledWith(expect.anything(), { limit: 50, offset: 2 });
    expect(text('.entry')).toHaveLength(3);
    expect(el.textContent).not.toContain('Show more');
  });

  it('offers to try again when the report fails', async () => {
    await render();
    api['summary']!.mockReturnValueOnce(throwError(() => new Error('down')));
    fixture.componentRef.setInput('period', 'all');
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Could not load the report.');
    button('Try again').click();
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')).toBeNull();
    expect(text('.total__value')[0]).toBe('€500.00');
  });
});
