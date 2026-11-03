import { completedText, goalCard } from './goal-view';
import { goal } from './testing';

describe('goalCard', () => {
  it('shows progress and what to save each month', () => {
    const card = goalCard(goal());
    expect([card.title, card.amounts, card.percent, card.width]).toEqual([
      'Savings',
      '€500.00 of €2,000.00',
      '25%',
      25,
    ]);
    expect(card.pace).toBe('Save €500.00 a month to reach it by January 2027.');
    expect(card.notes).toEqual(['3 months left, this one included (89 days)']);
  });

  it('describes the emergency fund target', () => {
    const card = goalCard(
      goal({
        type: 'emergency_fund',
        label_name: 'Emergency Fund',
        months_of_expenses: 6,
        average_expenses: '1050.00',
        target_amount: '6300.00',
        deadline: null,
        months_left: null,
        days_left: null,
        per_month: null,
        remaining: '5800.00',
      }),
    );
    expect(card.title).toBe('Emergency fund');
    expect(goalCard(goal({ type: 'emergency_fund', label_name: 'Rainy day' })).title).toBe(
      'Emergency fund · Rainy day',
    );
    expect(card.pace).toBe('€5,800.00 to go, no deadline.');
    expect(card.notes).toEqual(['6 months of €1,050.00 average expenses']);
  });

  it('waits for a month of expenses before the emergency fund has a target', () => {
    const card = goalCard(
      goal({ type: 'emergency_fund', months_of_expenses: 3, target_amount: null, deadline: null }),
    );
    expect(card.amounts).toBe('€500.00');
    expect(card.pace).toBe('The target appears after your first complete month with expenses.');
  });

  it('flags an overdue goal and a manual progress, and caps the bar', () => {
    const overdue = goalCard(goal({ overdue: true, deadline: '2026-09-30', months_left: 0 }));
    expect(overdue.pace).toBe('The deadline (30 September 2026) has passed: €1,500.00 to go.');
    expect(overdue.notes).toEqual([]);
    const done = goalCard(goal({ reached: true, percent: '120.00', manual_progress: '2400.00' }));
    expect([done.pace, done.width, done.notes]).toEqual([
      'Target reached.',
      100,
      ['Progress set by hand'],
    ]);
  });
});

describe('completedText', () => {
  it('says when the goal was completed', () => {
    expect(completedText(goal({ completed_at: '2026-11-03T21:00:00Z' }))).toBe(
      'Completed on 3 November 2026',
    );
  });
});
