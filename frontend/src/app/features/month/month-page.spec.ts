import { Dialog } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { MonthRead, MonthSummary } from '../../core/api/types';
import MonthPage from './month-page';
import { MonthsApi } from './months-api';

const OCTOBER: MonthRead = { id: 'm10', year: 2026, month: 10, note: null, closed_at: null };

const SUMMARY: MonthSummary = {
  month_id: 'm10',
  year: 2026,
  month: 10,
  closed_at: null,
  income_total: '1050.00',
  distributed: '650.00',
  unallocated: '400.00',
  over_allocated: false,
  month_total: '650.00',
  by_kind: { expense: '212.00', saving: '288.00', investment: '150.00' },
  labels: [
    {
      label_id: 'food',
      name: 'Food',
      kind: 'expense',
      color: '#FFB74D',
      icon: 'restaurant',
      archived: false,
      allocation: '200.00',
      addition: '0.00',
      transfer_in: '12.00',
      transfer_out: '0.00',
      total: '212.00',
    },
  ],
};

describe('MonthPage', () => {
  let fixture: ComponentFixture<MonthPage>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let dialog: { open: ReturnType<typeof vi.fn> };

  async function render(find = vi.fn(() => of(OCTOBER))) {
    api = {
      find,
      summary: vi.fn(() => of(SUMMARY)),
      entries: vi.fn(() => of([])),
      create: vi.fn(() => of(OCTOBER)),
    };
    dialog = { open: vi.fn(() => ({ closed: of(OCTOBER) })) };
    TestBed.configureTestingModule({
      imports: [MonthPage],
      providers: [
        provideRouter([]),
        { provide: MonthsApi, useValue: api },
        { provide: Dialog, useValue: dialog },
      ],
    });
    fixture = TestBed.createComponent(MonthPage);
    fixture.componentRef.setInput('year', '2026');
    fixture.componentRef.setInput('month', '10');
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const text = (selector: string) =>
    [...el.querySelectorAll(selector)].map((e) => e.textContent?.replace(/\s+/g, ' ').trim());

  it('shows the month with totals, donut, labels and links to the next and previous months', async () => {
    await render();

    expect(el.querySelector('h1')?.textContent).toBe('October 2026');
    expect(api['find']).toHaveBeenCalledWith(2026, 10);
    expect(text('.total__value')).toEqual([
      '€1,050.00',
      '€212.00',
      '€288.00',
      '€150.00',
      '€400.00',
    ]);
    expect(el.querySelector('app-donut')).not.toBeNull();
    expect(text('.label-row__name')).toEqual(['Food']);
    expect(text('.label-row__detail')).toEqual(['Base €200.00 · +€12.00 moved in']);
    const links = [...el.querySelectorAll<HTMLAnchorElement>('.picker a')];
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/month/2026/9', '/month/2026/11']);
    expect(links[0]!.getAttribute('aria-label')).toBe('Previous month: September 2026');
  });

  it('switches the donut between kinds (Overview) and labels (Detailed), and remembers it', async () => {
    localStorage.clear();
    await render();
    const toggle = (name: string) =>
      [...el.querySelectorAll<HTMLButtonElement>('.toggle__option')].find(
        (b) => b.textContent?.trim() === name,
      )!;
    const legend = () => text('app-donut .legend__item').map((t) => t?.split(' ')[0]);

    expect(toggle('Overview').getAttribute('aria-pressed')).toBe('true');
    expect(legend()).toEqual(['Spent', 'Saved', 'Invested']);

    toggle('Detailed').click();
    await fixture.whenStable();
    expect(toggle('Detailed').getAttribute('aria-pressed')).toBe('true');
    expect(el.querySelector('figcaption')?.textContent?.trim()).toBe('Distribution by label');
    expect(legend()).toEqual(['Food']);
    expect(localStorage.getItem('fs.month.donut')).toBe('detailed');

    toggle('Overview').click();
    expect(localStorage.getItem('fs.month.donut')).toBeNull();
  });

  it('offers to create a month that does not exist yet', async () => {
    const find = vi.fn().mockReturnValueOnce(of(null)).mockReturnValue(of(OCTOBER));
    await render(find);

    expect(el.querySelector('.empty h2')?.textContent).toContain('No sheet for October 2026 yet');
    el.querySelector<HTMLButtonElement>('.empty button')!.click();
    await fixture.whenStable();

    expect(dialog.open.mock.calls[0]![1].data).toEqual({ year: 2026, month: 10 });
    expect(text('.total__value')[0]).toBe('€1,050.00');
  });

  it('opens the New month dialog for the following month', async () => {
    await render();
    [...el.querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.includes('New month'))!
      .click();
    expect(dialog.open.mock.calls[0]![1].data).toEqual({ year: 2026, month: 11 });
  });

  it('reports a failure to load', async () => {
    await render(vi.fn(() => throwError(() => new Error('down'))));
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Could not load October 2026');
  });
});
