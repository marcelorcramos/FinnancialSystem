import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { LimitRead } from '../../core/api/types';
import { LimitDialog } from './limit-dialog';
import { LimitsApi } from './limits-api';

const DATA = {
  monthId: 'm11',
  monthTitle: 'November 2026',
  labelId: 'food',
  labelName: 'Food',
  total: '240.00',
};

describe('LimitDialog', () => {
  let fixture: ComponentFixture<LimitDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(limits: LimitRead[]) {
    api = {
      list: vi.fn(() => of(limits)),
      set: vi.fn(() => of({})),
      remove: vi.fn(() => of(undefined)),
    };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [LimitDialog],
      providers: [
        { provide: LimitsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: DATA },
      ],
    });
    fixture = TestBed.createComponent(LimitDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const button = (name: string) =>
    [...el.querySelectorAll<HTMLButtonElement>('button')].find((b) =>
      b.textContent?.includes(name),
    )!;
  const amount = () => el.querySelector<HTMLInputElement>('#limit-amount')!;

  async function type(value: string) {
    amount().value = value;
    amount().dispatchEvent(new Event('input'));
    await fixture.whenStable();
  }

  it('sets a limit for every month and previews this month', async () => {
    await render([]);
    expect(button('Save limit').disabled).toBe(true);
    await type('300');
    expect(el.querySelector('#limit-preview')?.textContent?.trim()).toBe(
      '€240.00 of €300.00 this month · 80%',
    );
    button('Save limit').click();
    expect(api['set']).toHaveBeenCalledWith('food', '300.00', null);
    expect(close).toHaveBeenCalledWith(true);
  });

  it('starts from this month’s own limit and can remove it', async () => {
    await render([
      { id: 'd', label_id: 'food', month_id: null, amount: '300.00' },
      { id: 'm', label_id: 'food', month_id: 'm11', amount: '200.00' },
      { id: 'x', label_id: 'other', month_id: null, amount: '50.00' },
    ]);
    const radios = el.querySelectorAll<HTMLInputElement>('input[name=scope]');
    expect(radios[1]!.checked).toBe(true);
    expect(amount().value).toBe('200.00');

    button('Remove this month’s limit').click();
    expect(api['remove']).toHaveBeenCalledWith('food', 'm11');
  });

  it('switches to only this month', async () => {
    await render([{ id: 'd', label_id: 'food', month_id: null, amount: '300.00' }]);
    el.querySelectorAll<HTMLInputElement>('input[name=scope]')[1]!.click();
    await fixture.whenStable();
    await type('150');
    button('Save limit').click();
    expect(api['set']).toHaveBeenCalledWith('food', '150.00', 'm11');
  });
});
