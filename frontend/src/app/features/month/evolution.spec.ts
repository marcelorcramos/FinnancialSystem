import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { LabelSummary, ReportSeries } from '../../core/api/types';
import { ReportsApi } from '../reports/reports-api';
import { Evolution } from './evolution';

function label(name: string, kind: LabelSummary['kind'], extra: Partial<LabelSummary> = {}) {
  return {
    label_id: name.toLowerCase(),
    name,
    kind,
    color: '#FFB74D',
    icon: 'restaurant',
    archived: false,
    allocation: '0.00',
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total: '0.00',
    ...extra,
  } as LabelSummary;
}

const LABELS = [
  label('Food', 'expense'),
  label('Water', 'expense', { color: '#4FC3F7' }),
  label('Savings', 'saving'),
  label('Gym', 'expense', { archived: true }),
];

function series(labelId: string, totals: string[], start = 5): ReportSeries {
  const months = totals.map((_, i) => `2026-${String(start + i).padStart(2, '0')}`);
  return {
    period: 'last_6_months',
    start_month: months[0]!,
    end_month: months.at(-1)!,
    reference_date: '2026-10-28',
    months,
    totals: [],
    labels: [
      {
        label_id: labelId,
        name: labelId,
        kind: 'expense',
        color: '#FFB74D',
        icon: 'restaurant',
        archived: false,
        total: '0.00',
        points: months.map((month, i) => ({ month, total: totals[i]! })),
      },
    ],
  };
}

describe('Evolution', () => {
  let fixture: ComponentFixture<Evolution>;
  let el: HTMLElement;
  let api: { series: ReturnType<typeof vi.fn> };

  async function render(preferred: string | null = 'water') {
    api = {
      series: vi.fn(({ labelIds }: { labelIds: string[] }) =>
        of(
          series(
            labelIds[0]!,
            labelIds[0] === 'food'
              ? ['0.00', '0.00', '0.00', '0.00', '200.00', '250.00']
              : ['30.00', '30.00', '30.00', '30.00', '30.00', '33.00'],
          ),
        ),
      ),
    };
    TestBed.configureTestingModule({
      imports: [Evolution],
      providers: [{ provide: ReportsApi, useValue: api }],
    });
    fixture = TestBed.createComponent(Evolution);
    fixture.componentRef.setInput('labels', LABELS);
    fixture.componentRef.setInput('preferred', preferred);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const stats = () => [...el.querySelectorAll('dd')].map((d) => d.textContent?.trim());
  async function choose(id: string, value: string) {
    const select = el.querySelector<HTMLSelectElement>(id)!;
    select.value = value;
    select.dispatchEvent(new Event('change'));
    await fixture.whenStable();
  }

  beforeEach(() => localStorage.clear());

  it('starts on the preferred label over the last 6 months', async () => {
    await render();
    expect(api.series).toHaveBeenCalledWith({ period: 'last_6_months', labelIds: ['water'] });
    expect(el.querySelector<HTMLSelectElement>('#evolution-label')!.value).toBe('water');
    expect(stats()).toEqual(['€33.00', '€30.50', '+10.0%']);
    expect([...el.querySelectorAll('dt')].at(-1)?.textContent).toBe('vs. May');
    expect(el.querySelector('app-line-chart svg')?.getAttribute('aria-label')).toBe(
      'Water over the last 6 months: May €30.00, Jun €30.00, Jul €30.00, Aug €30.00, Sep €30.00, Oct €33.00',
    );
  });

  it('groups usable labels by kind', async () => {
    await render();
    const groups = [...el.querySelectorAll('optgroup')].map((g) => [
      g.getAttribute('label'),
      [...g.querySelectorAll('option')].map((o) => o.textContent?.trim()),
    ]);
    expect(groups).toEqual([
      ['Expense', ['Food', 'Water']],
      ['Saving', ['Savings']],
    ]);
  });

  it('changes label and period, and remembers both', async () => {
    await render();
    await choose('#evolution-label', 'food');
    expect(stats()).toEqual(['€250.00', '€75.00', 'New']);
    await choose('#evolution-period', 'all');
    expect(api.series).toHaveBeenLastCalledWith({ period: 'all', labelIds: ['food'] });
    expect(localStorage.getItem('fs.month.evolution.label')).toBe('food');
    expect(localStorage.getItem('fs.month.evolution.period')).toBe('all');
  });

  it('falls back to the first usable label', async () => {
    await render(null);
    expect(api.series).toHaveBeenCalledWith({ period: 'last_6_months', labelIds: ['food'] });
  });

  it('says when the series could not load', async () => {
    await render();
    api.series.mockReturnValue(throwError(() => new Error('down')));
    await choose('#evolution-period', 'last_12_months');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Could not load');
  });
});
