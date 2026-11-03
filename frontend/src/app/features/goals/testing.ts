import { GoalRead } from '../../core/api/types';

/** A goal as the API returns it (fixture for the specs). */
export function goal(extra: Partial<GoalRead> = {}): GoalRead {
  return {
    id: 'g1',
    label_id: 'savings',
    label_name: 'Savings',
    color: '#5FD39A',
    icon: 'savings',
    type: 'normal',
    target_amount: '2000.00',
    months_of_expenses: null,
    average_expenses: null,
    deadline: '2027-01-31',
    manual_progress: null,
    progress: '500.00',
    remaining: '1500.00',
    percent: '25.00',
    months_left: 3,
    days_left: 89,
    per_month: '500.00',
    reached: false,
    overdue: false,
    completed_at: null,
    created_at: '2026-11-03T10:00:00Z',
    ...extra,
  };
}
