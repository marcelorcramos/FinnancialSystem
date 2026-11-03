import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { LabelRead } from '../../core/api/types';
import { GoalDialog, GoalDialogData } from './goal-dialog';
import { GoalsApi } from './goals-api';
import { goal } from './testing';

function label(id: string, name: string): LabelRead {
  return { id, name, archived_at: null } as LabelRead;
}

const LABELS = [label('savings', 'Savings'), label('fund', 'Emergency Fund')];

describe('GoalDialog', () => {
  let fixture: ComponentFixture<GoalDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(data: GoalDialogData) {
    api = { create: vi.fn(() => of(goal())), update: vi.fn(() => of(goal())) };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [GoalDialog],
      providers: [
        { provide: GoalsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: data },
      ],
    });
    fixture = TestBed.createComponent(GoalDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  async function set(selector: string, value: string) {
    const field = el.querySelector<HTMLInputElement>(selector)!;
    field.value = value;
    field.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  }
  const submit = () => el.querySelector<HTMLButtonElement>('.actions .btn--primary')!;

  it('creates a goal with a target and a deadline', async () => {
    await render({ labels: LABELS });
    expect(submit().disabled).toBe(true);
    await set('#goal-target', '2000');
    await set('#goal-deadline', '2027-01-31');
    submit().click();
    expect(api['create']).toHaveBeenCalledWith({
      label_id: 'savings',
      type: 'normal',
      target_amount: '2000.00',
      months_of_expenses: null,
      deadline: '2027-01-31',
      manual_progress: null,
    });
    expect(close).toHaveBeenCalled();
  });

  it('creates the emergency fund in the Emergency Fund label', async () => {
    await render({ labels: LABELS });
    el.querySelectorAll<HTMLInputElement>('input[name=goal-type]')[1]!.click();
    await fixture.whenStable();
    expect(el.querySelector<HTMLSelectElement>('#goal-label')!.value).toBe('fund');
    await set('#goal-months', '3');
    submit().click();
    expect(api['create']).toHaveBeenCalledWith(
      expect.objectContaining({
        label_id: 'fund',
        type: 'emergency_fund',
        target_amount: null,
        months_of_expenses: 3,
        deadline: null,
      }),
    );
  });

  it('edits a goal, tracking progress by hand', async () => {
    await render({ labels: [LABELS[0]!], goal: goal() });
    expect(el.querySelector('input[name=goal-type]')).toBeNull();
    expect(el.querySelector<HTMLInputElement>('#goal-target')!.value).toBe('2000.00');
    el.querySelector<HTMLInputElement>('.check input')!.click();
    await fixture.whenStable();
    await set('#goal-manual', '750');
    submit().click();
    expect(api['update']).toHaveBeenCalledWith('g1', {
      target_amount: '2000.00',
      deadline: '2027-01-31',
      manual_progress: '750.00',
    });
  });
});
