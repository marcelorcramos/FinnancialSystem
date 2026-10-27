import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { LabelSummary, MonthSummary } from '../../core/api/types';
import { AddMoneyDialog, defaultDate } from './add-money-dialog';
import { MonthsApi } from './months-api';

function label(name: string, total: string, extra: Partial<LabelSummary> = {}): LabelSummary {
  return {
    label_id: name.toLowerCase(),
    name,
    kind: 'expense',
    color: '#FFB74D',
    icon: 'restaurant',
    archived: false,
    allocation: total,
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total,
    ...extra,
  };
}

const SUMMARY = {
  month_id: 'm10',
  year: 2026,
  month: 10,
  income_total: '1050.00',
  unallocated: '400.00',
  labels: [
    label('Food', '212.00'),
    label('Savings', '288.00'),
    label('Gym', '0.00', { archived: true }),
  ],
} as MonthSummary;

describe('defaultDate', () => {
  it('uses today inside the month and the first day otherwise', () => {
    expect(defaultDate(2026, 10, new Date(2026, 9, 27))).toBe('2026-10-27');
    expect(defaultDate(2026, 9, new Date(2026, 9, 27))).toBe('2026-09-01');
  });
});

describe('AddMoneyDialog', () => {
  let fixture: ComponentFixture<AddMoneyDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    api = { addMoney: vi.fn(() => of({})), transfer: vi.fn(() => of({})) };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [AddMoneyDialog],
      providers: [
        { provide: MonthsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: { summary: SUMMARY, labelId: 'food' } },
      ],
    });
    fixture = TestBed.createComponent(AddMoneyDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  async function set(selector: string, value: string, event = 'input') {
    const field = el.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
    field.value = value;
    field.dispatchEvent(new Event(event));
    await fixture.whenStable();
  }

  const submitButton = () => el.querySelector<HTMLButtonElement>('.actions .btn--primary')!;
  /** What a screen reader hears for each line of the impact panel. */
  const impact = () =>
    [...el.querySelectorAll('.impact__line .visually-hidden')].map((l) =>
      l.textContent?.replace(/\s+/g, ' ').trim(),
    );

  it('offers only active labels and starts on the chosen one', () => {
    const options = [...el.querySelectorAll('#add-target option')].map((o) =>
      o.textContent?.trim(),
    );
    expect(options).toEqual(['Food', 'Savings']);
    expect(el.querySelector<HTMLSelectElement>('#add-target')!.value).toBe('food');
    expect(submitButton().disabled).toBe(true);
  });

  it('adds money from outside the app, raising the income', async () => {
    await set('#add-amount', '20');
    await set('#add-date', '2026-10-15');
    await set('#add-source', 'Bonus');

    expect(impact()).toEqual([
      'Food: from €212.00 to €232.00',
      'Month income: from €1,050.00 to €1,070.00',
      'Unallocated: stays €400.00',
    ]);
    expect(submitButton().textContent?.trim()).toBe('Add €20.00');
    submitButton().click();

    expect(api['addMoney']).toHaveBeenCalledWith('m10', {
      label_id: 'food',
      amount: '20.00',
      occurred_on: '2026-10-15',
      source: 'Bonus',
    });
    expect(close).toHaveBeenCalledWith(true);
  });

  it('moves money from another label as a transfer', async () => {
    await set('#add-amount', '20');
    el.querySelectorAll<HTMLInputElement>('input[name=origin]')[1]!.click();
    await fixture.whenStable();

    expect(impact()).toEqual([
      'Food: from €212.00 to €232.00',
      'Savings: from €288.00 to €268.00',
      'Unallocated: stays €400.00',
    ]);
    submitButton().click();
    expect(api['transfer']).toHaveBeenCalledWith('m10', {
      from_label_id: 'savings',
      to_label_id: 'food',
      amount: '20.00',
      occurred_on: expect.stringMatching(/^2026-10-\d\d$/),
    });
  });

  it('shows the API message, e.g. for a closed month', async () => {
    api['addMoney']!.mockReturnValueOnce(
      throwError(
        () => new HttpErrorResponse({ status: 409, error: { detail: 'The month is closed.' } }),
      ),
    );
    await set('#add-amount', '5');
    submitButton().click();
    await fixture.whenStable();

    expect(el.querySelector('[role=alert]')?.textContent).toContain('The month is closed.');
    expect(close).not.toHaveBeenCalled();
  });
});
