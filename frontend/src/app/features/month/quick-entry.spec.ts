import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { LabelSummary, MonthSummary } from '../../core/api/types';
import { defaultDate } from './add-money-dialog';
import { MonthsApi } from './months-api';
import { QuickEntry } from './quick-entry';

function label(name: string, archived = false): LabelSummary {
  return {
    label_id: name.toLowerCase(),
    name,
    kind: 'expense',
    color: '#FFB74D',
    icon: 'restaurant',
    archived,
    allocation: '100.00',
    addition: '0.00',
    transfer_in: '0.00',
    transfer_out: '0.00',
    total: '100.00',
  };
}

const SUMMARY = {
  month_id: 'm10',
  year: 2026,
  month: 10,
  labels: [label('Food'), label('Savings'), label('Gym', true)],
} as MonthSummary;

describe('QuickEntry', () => {
  let fixture: ComponentFixture<QuickEntry>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let added: string[];

  beforeEach(async () => {
    api = { addMoney: vi.fn(() => of({})), transfer: vi.fn(() => of({})) };
    TestBed.configureTestingModule({
      imports: [QuickEntry],
      providers: [{ provide: MonthsApi, useValue: api }],
    });
    fixture = TestBed.createComponent(QuickEntry);
    fixture.componentRef.setInput('summary', SUMMARY);
    added = [];
    fixture.componentInstance.added.subscribe((text) => added.push(text));
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  async function set(selector: string, value: string, event = 'input') {
    const field = el.querySelector<HTMLInputElement | HTMLSelectElement>(selector)!;
    field.value = value;
    field.dispatchEvent(new Event(event));
    await fixture.whenStable();
  }

  const submit = () => el.querySelector<HTMLButtonElement>('button[type=submit]')!;
  const options = (selector: string) =>
    [...el.querySelectorAll(`${selector} option`)].map((o) => o.textContent?.trim());

  it('offers the active labels and starts from outside the app', () => {
    expect(options('#quick-to')).toEqual(['Food', 'Savings']);
    expect(options('#quick-from')).toEqual(['Outside the app', 'Savings']);
    expect(submit().disabled).toBe(true);
  });

  it('adds money from outside the app on the default date', async () => {
    await set('#quick-amount', '12,5');
    expect(submit().textContent?.trim()).toBe('Add €12.50');
    submit().click();
    await fixture.whenStable();

    expect(api['addMoney']).toHaveBeenCalledWith('m10', {
      label_id: 'food',
      amount: '12.50',
      occurred_on: defaultDate(2026, 10),
    });
    expect(added).toEqual(['€12.50 added to Food']);
    expect(el.querySelector<HTMLInputElement>('#quick-amount')!.value).toBe('');
  });

  it('moves money from another label as a transfer', async () => {
    await set('#quick-amount', '20');
    await set('#quick-to', 'savings', 'change');
    expect(options('#quick-from')).toEqual(['Outside the app', 'Food']);
    await set('#quick-from', 'food', 'change');
    expect(submit().textContent?.trim()).toBe('Move €20.00');
    submit().click();

    expect(api['transfer']).toHaveBeenCalledWith('m10', {
      from_label_id: 'food',
      to_label_id: 'savings',
      amount: '20.00',
      occurred_on: defaultDate(2026, 10),
    });
    expect(added).toEqual(['€20.00 moved from Food to Savings']);
  });

  it('shows the API message and keeps the amount', async () => {
    api['addMoney']!.mockReturnValueOnce(
      throwError(
        () => new HttpErrorResponse({ status: 409, error: { detail: 'The month is closed.' } }),
      ),
    );
    await set('#quick-amount', '5');
    submit().click();
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('The month is closed.');
    expect(el.querySelector<HTMLInputElement>('#quick-amount')!.value).toBe('5');
    expect(added).toEqual([]);
  });
});
