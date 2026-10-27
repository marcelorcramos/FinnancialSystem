import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { IncomeRead, LabelSummary, MonthRead, MonthSummary } from '../../core/api/types';
import { MonthsApi } from './months-api';
import { NewMonthDialog } from './new-month-dialog';

const OCTOBER: MonthRead = { id: 'm10', year: 2026, month: 10, note: null, closed_at: null };
const NOVEMBER: MonthRead = { id: 'm11', year: 2026, month: 11, note: null, closed_at: null };

function label(name: string, allocation: string, extra: Partial<LabelSummary> = {}): LabelSummary {
  return {
    label_id: name.toLowerCase(),
    name,
    kind: 'expense',
    color: '#FFB74D',
    icon: 'restaurant',
    archived: false,
    allocation,
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total: allocation,
    ...extra,
  };
}

const SUMMARY = {
  labels: [
    label('Housing', '650.00'),
    label('Food', '200.00'),
    label('Subscriptions', '22.00'),
    label('Water', '0.00'),
    label('Gym', '30.00', { archived: true }),
  ],
} as MonthSummary;

function income(id: string, source: string, amount: string, fromAddition = false): IncomeRead {
  return {
    id,
    month_id: 'm10',
    source,
    amount,
    received_on: '2026-10-01',
    note: null,
    from_addition: fromAddition,
  };
}

describe('NewMonthDialog', () => {
  let fixture: ComponentFixture<NewMonthDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(months: MonthRead[] = [OCTOBER]) {
    api = {
      list: vi.fn((year: number) => of(months.filter((m) => m.year === year))),
      summary: vi.fn(() => of(SUMMARY)),
      incomes: vi.fn((id: string) =>
        of(
          id === 'm10'
            ? [income('i1', 'Salary', '2000.00'), income('i2', 'Freelance', '50.00', true)]
            : [income('c1', 'Salary', '2000.00')],
        ),
      ),
      create: vi.fn(() => of(NOVEMBER)),
      setAllocation: vi.fn(() => of(null)),
      updateIncome: vi.fn(() => of({})),
    };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [NewMonthDialog],
      providers: [
        { provide: MonthsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: { year: 2026, month: 11 } },
      ],
    });
    fixture = TestBed.createComponent(NewMonthDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  /** A button by its visible text or its aria-label. */
  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.getAttribute('aria-label') === name || b.textContent?.includes(name),
    )!;
  const summary = () => [...el.querySelectorAll('.summary .num')].map((n) => n.textContent?.trim());

  async function input(label: string, value: string) {
    const field = el.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!;
    field.value = value;
    field.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  }

  it('starts from the previous month, without archived or empty labels and one-off incomes', async () => {
    await render();
    expect(el.querySelector('legend')?.textContent).toContain('October 2026');
    expect(el.querySelector('.option__text')?.textContent).toContain('3 labels');
    expect(el.querySelector('.option__text')?.textContent).toContain('€872.00');
    expect([...el.querySelectorAll('.income__label')].map((l) => l.textContent?.trim())).toEqual([
      'Salary',
    ]);
    expect(summary()).toEqual(['€2,000.00', '€872.00', '€1,128.00']);
  });

  it('lets each amount be reviewed against the previous month', async () => {
    await render();
    button('Review amounts').click();
    await fixture.whenStable();

    button('Increase Food by €10').click();
    button('Increase Food by €10').click();
    await input('Housing amount for November 2026', '700');
    button('Remove Subscriptions').click();
    await fixture.whenStable();

    const deltas = [...el.querySelectorAll('.review__delta')].map((d) => d.textContent?.trim());
    expect(deltas).toEqual(['+€50.00 vs. before', '+€20.00 vs. before', 'Not in the new month']);
    expect(summary()).toEqual(['€2,000.00', '€920.00', '€1,080.00']);

    button('Reset to October 2026').click();
    await fixture.whenStable();
    expect(summary()[1]).toBe('€872.00');
  });

  it('creates the month copying, then sends only the reviewed changes', async () => {
    await render();
    button('Review amounts').click();
    await fixture.whenStable();
    button('Increase Food by €10').click();
    button('Remove Subscriptions').click();
    const salary = el.querySelector<HTMLInputElement>('#income-i1')!;
    salary.value = '2100';
    salary.dispatchEvent(new Event('input'));
    await fixture.whenStable();

    button('Create November 2026').click();
    await fixture.whenStable();

    expect(api['create']).toHaveBeenCalledWith({
      year: 2026,
      month: 11,
      note: null,
      copy_allocations: true,
      copy_incomes: true,
    });
    expect(api['setAllocation'].mock.calls).toEqual([
      ['m11', 'food', { amount: '210.00' }],
      ['m11', 'subscriptions', { amount: '0.00' }],
    ]);
    expect(api['updateIncome']).toHaveBeenCalledWith('c1', { amount: '2100.00' });
    expect(close).toHaveBeenCalledWith(NOVEMBER);
  });

  it('blocks creating while an amount is not valid', async () => {
    await render();
    button('Review amounts').click();
    await fixture.whenStable();
    await input('Food amount for November 2026', 'abc');
    expect(button('Create November 2026').disabled).toBe(true);
  });

  it('turns off the copies when the previous month has nothing to copy', async () => {
    await render();
    api['summary']!.mockReturnValue(of({ labels: [] }));
    api['incomes']!.mockReturnValue(of([]));
    fixture = TestBed.createComponent(NewMonthDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();

    const boxes = [...el.querySelectorAll<HTMLInputElement>('input[type=checkbox]')];
    expect(boxes.map((b) => [b.checked, b.disabled])).toEqual([
      [false, true],
      [false, true],
    ]);
    expect(el.textContent).toContain('Nothing to copy: October 2026 has no initial distribution.');
  });

  it('starts empty when there is no previous month', async () => {
    await render([]);
    expect(el.textContent).toContain('This is your first month');
    button('Create November 2026').click();
    await fixture.whenStable();
    expect(api['create']).toHaveBeenCalledWith(
      expect.objectContaining({ copy_allocations: false, copy_incomes: false }),
    );
  });
});
