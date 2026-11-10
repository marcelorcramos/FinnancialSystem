import { Dialog } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import {
  AttachmentRead,
  EntryListItem,
  LimitStatus,
  MonthRead,
  MonthSummary,
  ReportSeries,
} from '../../core/api/types';
import { ToastService } from '../../shared/ui/toast.service';
import MonthPage from './month-page';
import { ReportsApi } from '../reports/reports-api';
import { LimitsApi } from './limits-api';
import { MonthsApi } from './months-api';
import { PlanMonthDialog } from './plan-month-dialog';
import { ReceiptsApi } from './receipts-api';
import { ReceiptsDialog } from './receipts-dialog';

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

const ENTRY: EntryListItem = {
  id: 'e1',
  month_id: 'm10',
  label_id: 'food',
  amount: '200.00',
  movement_type: 'allocation',
  transfer_id: null,
  income_id: null,
  occurred_on: '2026-10-01',
  note: null,
  created_at: '2026-10-01T09:00:00Z',
  origin: 'initial_distribution',
  source: null,
  counterpart_label_id: null,
};

const RECEIPT: AttachmentRead = {
  id: 'r1',
  month_id: 'm10',
  entry_id: 'e1',
  filename: 'groceries.pdf',
  mime: 'application/pdf',
  size: 2048,
  created_at: '2026-10-02T09:00:00Z',
};

const SERIES = {
  months: ['2026-09', '2026-10'],
  labels: [
    {
      label_id: 'food',
      name: 'Food',
      total: '412.00',
      points: [
        { month: '2026-09', total: '200.00' },
        { month: '2026-10', total: '212.00' },
      ],
    },
  ],
} as ReportSeries;

describe('MonthPage', () => {
  let fixture: ComponentFixture<MonthPage>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let limitsApi: { status: ReturnType<typeof vi.fn> };
  let limitsApiFailing = false;
  let receiptsApi: { list: ReturnType<typeof vi.fn> };

  afterEach(() => (limitsApiFailing = false));
  let dialog: { open: ReturnType<typeof vi.fn>; openDialogs: unknown[] };

  async function render(find = vi.fn(() => of(OCTOBER))) {
    api = {
      find,
      summary: vi.fn(() => of(SUMMARY)),
      entries: vi.fn(() => of([])),
      create: vi.fn(() => of(OCTOBER)),
      deleteEntry: vi.fn(() => of(undefined)),
      restoreEntry: vi.fn(() => of({})),
      close: vi.fn(() => of({ ...OCTOBER, closed_at: '2026-10-31T10:00:00Z' })),
      reopen: vi.fn(() => of(OCTOBER)),
    };
    dialog = { open: vi.fn(() => ({ closed: of(OCTOBER) })), openDialogs: [] };
    limitsApi = {
      status: vi.fn(() =>
        limitsApiFailing ? throwError(() => new Error('limits are down')) : of([] as LimitStatus[]),
      ),
    };
    receiptsApi = { list: vi.fn(() => of([] as AttachmentRead[])) };
    TestBed.configureTestingModule({
      imports: [MonthPage],
      providers: [
        provideRouter([]),
        { provide: MonthsApi, useValue: api },
        { provide: Dialog, useValue: dialog },
        { provide: ReportsApi, useValue: { series: vi.fn(() => of(SERIES)) } },
        { provide: LimitsApi, useValue: limitsApi },
        { provide: ReceiptsApi, useValue: receiptsApi },
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
    expect(el.querySelector('app-evolution .evolution__stats')?.textContent).toContain('€212.00');
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

  it('opens the Plan dialog with the month summary and reloads after saving', async () => {
    dialog.open = vi.fn(() => ({ closed: of(true) }));
    await render();
    dialog.open = vi.fn(() => ({ closed: of(true) }));
    [...el.querySelectorAll<HTMLButtonElement>('button')]
      .find((b) => b.textContent?.trim() === 'Plan')!
      .click();
    await fixture.whenStable();
    expect(dialog.open.mock.calls[0]![0]).toBe(PlanMonthDialog);
    expect(dialog.open.mock.calls[0]![1].data).toEqual({ summary: SUMMARY });
    expect(api['summary']).toHaveBeenCalledTimes(2);
  });

  it('deletes an entry and brings it back with Undo', async () => {
    await render();
    api['entries']!.mockReturnValue(of([ENTRY]));
    fixture.componentRef.setInput('month', '9');
    fixture.componentRef.setInput('month', '10');
    await fixture.whenStable();
    const toasts = TestBed.inject(ToastService);

    el.querySelector<HTMLButtonElement>('button[aria-label="Delete Food"]')!.click();
    await fixture.whenStable();
    expect(api['deleteEntry']).toHaveBeenCalledWith('e1');
    const toast = toasts.toasts().at(-1)!;
    expect(toast.message).toBe('“Food” deleted');

    toasts.act(toast);
    expect(api['restoreEntry']).toHaveBeenCalledWith('e1');
  });

  it('closes the month, hiding the write actions, and reopens it', async () => {
    await render();
    const button = (name: string) =>
      [...el.querySelectorAll<HTMLButtonElement>('button')].find((b) =>
        b.textContent?.includes(name),
      );

    api['find']!.mockReturnValue(of({ ...OCTOBER, closed_at: '2026-10-31T10:00:00Z' }));
    button('Close month')!.click();
    await fixture.whenStable();
    expect(api['close']).toHaveBeenCalledWith('m10');
    expect(el.querySelector('.chip')?.textContent).toBe('Closed');
    expect(button('Add money')).toBeUndefined();
    expect(button('Plan')).toBeUndefined();
    expect(el.querySelector('app-quick-entry')).toBeNull();

    api['find']!.mockReturnValue(of(OCTOBER));
    button('Reopen')!.click();
    await fixture.whenStable();
    expect(api['reopen']).toHaveBeenCalledWith('m10');
    expect(button('Add money')).toBeDefined();
  });

  it('lists every entry on demand and adds quick entries', async () => {
    await render();
    const many = Array.from({ length: 8 }, (_, i) => ({
      ...ENTRY,
      id: `e${i}`,
      occurred_on: `2026-10-0${i + 1}`,
    }));
    api['entries']!.mockReturnValue(of(many));
    fixture.componentInstance['reload']();
    await fixture.whenStable();

    expect(el.querySelectorAll('.entry')).toHaveLength(6);
    const toggle = [...el.querySelectorAll<HTMLButtonElement>('.recent .more')][0]!;
    expect(toggle.textContent?.trim()).toBe('Show all 8 entries');
    toggle.click();
    await fixture.whenStable();
    expect(el.querySelectorAll('.entry')).toHaveLength(8);
    expect(el.querySelector('.recent .more')?.textContent?.trim()).toBe('Show the latest 6');
    expect(el.querySelector('app-quick-entry')).not.toBeNull();
  });

  it('answers the keyboard shortcuts unless typing', async () => {
    await render();
    const router = TestBed.inject(Router);
    const go = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    const press = (
      key: string,
      init: KeyboardEventInit = {},
      target: EventTarget = document.body,
    ) => target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }));

    press('n');
    expect(document.activeElement?.id).toBe('quick-amount');
    press('ArrowRight', {}, document.activeElement!); // typing in a field: ignored
    expect(go).not.toHaveBeenCalled();
    (document.activeElement as HTMLElement).blur();

    press('t');
    expect(document.activeElement?.id).toBe('quick-from');
    (document.activeElement as HTMLElement).blur();

    press('ArrowLeft');
    press('ArrowRight');
    expect(go.mock.calls.map((c) => c[0])).toEqual(['/month/2026/9', '/month/2026/11']);

    const toasts = TestBed.inject(ToastService);
    const undo = vi.spyOn(toasts, 'undoLatest').mockReturnValue(true);
    press('z', { ctrlKey: true });
    expect(undo).toHaveBeenCalledOnce();
  });

  it('shows how much of its limit a label used and opens the limit dialog', async () => {
    await render();
    limitsApi.status.mockReturnValue(
      of([
        {
          label_id: 'food',
          name: 'Food',
          color: '#FFB74D',
          limit_id: 'l1',
          limit: '250.00',
          source: 'default',
          total: '212.00',
          remaining: '38.00',
          percent: '84.80',
          level: 'warning',
        },
      ] as LimitStatus[]),
    );
    fixture.componentInstance['reload']();
    await fixture.whenStable();

    const usage = el.querySelector('.limit');
    expect(usage?.getAttribute('data-level')).toBe('warning');
    expect(usage?.textContent?.replace(/\s+/g, ' ').trim()).toBe(
      'Near the limit: €212.00 of €250.00 · 85%',
    );
    el.querySelector<HTMLButtonElement>('[aria-label="Limit for Food"]')!.click();
    expect(dialog.open).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        data: {
          monthId: 'm10',
          monthTitle: 'October 2026',
          labelId: 'food',
          labelName: 'Food',
          total: '212.00',
        },
      }),
    );
  });

  it('still shows the month when the limits cannot load', async () => {
    limitsApiFailing = true;
    await render();
    expect(el.querySelector('h1')?.textContent).toBe('October 2026');
    expect(el.querySelector('.limit')).toBeNull();
    expect(el.querySelectorAll('.label-row').length).toBeGreaterThan(0);
  });

  it('counts receipts per entry and opens them for one entry or the whole month', async () => {
    const entries = vi.fn(() => of([ENTRY]));
    await render();
    api['entries'] = entries;
    receiptsApi.list.mockReturnValue(of([RECEIPT, { ...RECEIPT, id: 'r2', entry_id: null }]));
    fixture.componentInstance['reload']();
    await fixture.whenStable();

    const button = el.querySelector<HTMLButtonElement>('.entry__receipts')!;
    expect(button.getAttribute('aria-label')).toBe('Receipts for Food (1)');
    expect(el.querySelector('.head__actions .count')?.textContent).toBe('2');

    button.click();
    expect(dialog.open).toHaveBeenLastCalledWith(
      ReceiptsDialog,
      expect.objectContaining({
        data: expect.objectContaining({
          monthId: 'm10',
          entry: { id: 'e1', title: 'Food' },
          closed: false,
        }),
      }),
    );
    // Closing the dialog reloads the receipts.
    expect(receiptsApi.list).toHaveBeenLastCalledWith('m10');

    el.querySelector<HTMLButtonElement>('.head__actions .btn')!.click();
    expect(dialog.open).toHaveBeenLastCalledWith(
      ReceiptsDialog,
      expect.objectContaining({ data: expect.objectContaining({ entry: null }) }),
    );
  });

  it('reports a failure to load', async () => {
    await render(vi.fn(() => throwError(() => new Error('down'))));
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Could not load October 2026');
  });
});
