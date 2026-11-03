import { Dialog } from '@angular/cdk/dialog';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { GoalList, LabelRead } from '../../core/api/types';
import { ToastService } from '../../shared/ui/toast.service';
import { LabelsApi } from '../labels/labels-api';
import { GoalsApi } from './goals-api';
import GoalsPage from './goals-page';
import { goal } from './testing';

const LIST: GoalList = {
  active: [goal()],
  completed: [
    goal({
      id: 'g0',
      label_name: 'Trip',
      reached: true,
      progress: '800.00',
      target_amount: '800.00',
      completed_at: '2026-10-20T10:00:00Z',
    }),
  ],
};

describe('GoalsPage', () => {
  let fixture: ComponentFixture<GoalsPage>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let dialog: { open: ReturnType<typeof vi.fn> };
  let toasts: { show: ReturnType<typeof vi.fn> };

  async function render(list: GoalList = LIST) {
    api = {
      list: vi.fn(() => of(list)),
      delete: vi.fn(() => of(undefined)),
      restore: vi.fn(() => of(goal())),
    };
    dialog = { open: vi.fn(() => ({ closed: of(goal()) })) };
    toasts = { show: vi.fn() };
    const labels = [
      { id: 'savings', name: 'Savings', archived_at: null },
      { id: 'fund', name: 'Emergency Fund', archived_at: null },
      { id: 'old', name: 'Old', archived_at: '2026-01-01T00:00:00Z' },
    ] as LabelRead[];
    TestBed.configureTestingModule({
      imports: [GoalsPage],
      providers: [
        { provide: GoalsApi, useValue: api },
        { provide: LabelsApi, useValue: { list: vi.fn(() => of(labels)) } },
        { provide: Dialog, useValue: dialog },
        { provide: ToastService, useValue: toasts },
      ],
    });
    fixture = TestBed.createComponent(GoalsPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const text = (selector: string) =>
    [...el.querySelectorAll(selector)].map((e) => e.textContent?.replace(/\s+/g, ' ').trim());

  it('shows active goals with their pace and the completed ones', async () => {
    await render();
    expect(text('.goal h2')).toEqual(['Savings']);
    expect(text('.goal__amounts')).toEqual(['€500.00 of €2,000.00']);
    expect(el.querySelector('[role=progressbar]')?.getAttribute('aria-valuenow')).toBe('25');
    expect(text('.goal__pace')).toEqual(['Save €500.00 a month to reach it by January 2027.']);
    expect(text('.done__text strong')).toEqual(['Trip']);
    expect(text('.done__text .muted')).toEqual(['Completed on 20 October 2026']);
  });

  it('offers only labels without an active goal for a new one', async () => {
    await render();
    el.querySelector<HTMLButtonElement>('.head .btn--primary')!.click();
    const data = dialog.open.mock.calls[0]![1].data;
    expect(data.labels.map((l: LabelRead) => l.id)).toEqual(['fund']);
    expect(toasts.show).toHaveBeenCalledWith('Goal created');
  });

  it('deletes a goal with Undo', async () => {
    await render();
    el.querySelector<HTMLButtonElement>('[aria-label="Delete goal for Savings"]')!.click();
    expect(api['delete']).toHaveBeenCalledWith('g1');
    const [message, action] = toasts.show.mock.calls[0]!;
    expect(message).toBe('Goal for Savings deleted');
    action.run();
    expect(api['restore']).toHaveBeenCalledWith('g1');
  });

  it('invites to create the first goal', async () => {
    await render({ active: [], completed: [] });
    expect(el.querySelector('.empty h2')?.textContent).toBe('No goals yet');
  });
});
