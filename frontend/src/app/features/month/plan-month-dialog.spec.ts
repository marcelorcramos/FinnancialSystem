import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { IncomeRead, LabelSummary, MonthSummary } from '../../core/api/types';
import { MonthsApi } from './months-api';
import { PlanMonthDialog } from './plan-month-dialog';

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
  month_id: 'm10',
  year: 2026,
  month: 10,
  labels: [
    label('Food', '200.00'),
    label('Housing', '0.00'),
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

describe('PlanMonthDialog', () => {
  let fixture: ComponentFixture<PlanMonthDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(incomes: IncomeRead[]) {
    api = {
      incomes: vi.fn(() => of(incomes)),
      addIncome: vi.fn(() => of({})),
      updateIncome: vi.fn(() => of({})),
      deleteIncome: vi.fn(() => of(undefined)),
      setAllocation: vi.fn(() => of(null)),
    };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [PlanMonthDialog],
      providers: [
        { provide: MonthsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: { summary: SUMMARY } },
      ],
    });
    fixture = TestBed.createComponent(PlanMonthDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find(
      (b) => b.getAttribute('aria-label') === name || b.textContent?.includes(name),
    )!;
  const saveButton = () => el.querySelector<HTMLButtonElement>('.actions .btn--primary')!;
  const summary = () => [...el.querySelectorAll('.summary .num')].map((n) => n.textContent?.trim());

  async function input(label: string, value: string) {
    const field = el.querySelector<HTMLInputElement>(`input[aria-label="${label}"]`)!;
    field.value = value;
    field.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  }

  it('lists recurring incomes, extras and every usable label', async () => {
    await render([income('i1', 'Salary', '1000.00'), income('i2', 'Bonus', '50.00', true)]);
    expect(el.querySelector<HTMLInputElement>('input[aria-label="Income name 1"]')!.value).toBe(
      'Salary',
    );
    expect(el.querySelector('.plan-extra')?.textContent?.replace(/\s+/g, ' ')).toContain(
      'Extra income · 1 entry€50.00',
    );
    expect(el.querySelector('.review__delta')).toBeNull(); // nothing changed yet
    expect(
      [...el.querySelectorAll('.review__name > span:first-child')].map((n) => n.textContent),
    ).toEqual(['Food', 'Housing']);
    expect(summary()).toEqual(['€1,050.00', '€200.00', '€850.00']);
    expect(saveButton().textContent?.trim()).toBe('Done');
  });

  it('adds a salary and distributes it, sending only the changes', async () => {
    await render([]);
    expect(el.textContent).toContain('No income yet');
    button('Add income').click();
    await fixture.whenStable();
    expect(el.querySelector<HTMLInputElement>('input[aria-label="Income name 1"]')!.value).toBe(
      'Salary',
    );
    expect(saveButton().disabled).toBe(true); // no amount yet

    await input('Salary amount', '1500');
    await input('Housing amount for October 2026', '650');
    button('Increase Food by €10').click();
    await fixture.whenStable();

    expect(summary()).toEqual(['€1,500.00', '€860.00', '€640.00']);
    expect(saveButton().textContent?.trim()).toBe('Save 3 changes');
    saveButton().click();
    await fixture.whenStable();

    expect(api['addIncome']).toHaveBeenCalledWith('m10', {
      source: 'Salary',
      amount: '1500.00',
      received_on: '2026-10-01',
    });
    expect(api['setAllocation'].mock.calls).toEqual([
      ['m10', 'food', { amount: '210.00' }],
      ['m10', 'housing', { amount: '650.00' }],
    ]);
    expect(close).toHaveBeenCalledWith(true);
  });

  it('edits and removes saved incomes', async () => {
    await render([income('i1', 'Salary', '1000.00'), income('i3', 'Rent from room', '300.00')]);
    await input('Salary amount', '1100');
    button('Remove Rent from room').click();
    await fixture.whenStable();
    expect(summary()[0]).toBe('€1,100.00');

    saveButton().click();
    await fixture.whenStable();
    expect(api['updateIncome']).toHaveBeenCalledWith('i1', { source: 'Salary', amount: '1100.00' });
    expect(api['deleteIncome']).toHaveBeenCalledWith('i3');
    expect(api['setAllocation']).not.toHaveBeenCalled();
  });

  it('blocks saving while an amount is not valid', async () => {
    await render([income('i1', 'Salary', '1000.00')]);
    await input('Food amount for October 2026', 'abc');
    expect(saveButton().disabled).toBe(true);
    expect(el.querySelector('.review__delta')?.textContent).toContain('Not an amount');
  });

  it('shows the API message and stays open', async () => {
    await render([income('i1', 'Salary', '1000.00')]);
    api['setAllocation']!.mockReturnValueOnce(
      throwError(
        () => new HttpErrorResponse({ status: 409, error: { detail: 'The month is closed.' } }),
      ),
    );
    await input('Food amount for October 2026', '250');
    saveButton().click();
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('The month is closed.');
    expect(close).not.toHaveBeenCalled();
  });
});
