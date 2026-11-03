import { GoalRead } from '../../core/api/types';
import { formatMoney } from '../../shared/money/format-money';

export interface GoalCard {
  id: string;
  title: string;
  emergency: boolean;
  color: string;
  icon: string;
  /** "€500.00 of €2,000.00" */
  amounts: string;
  percent: string;
  /** Bar width, 0–100. */
  width: number;
  /** One line about the pace, e.g. "Save €500.00 a month to reach it by January 2027". */
  pace: string;
  /** Extra lines (time left, how the target was set...). */
  notes: string[];
  overdue: boolean;
  reached: boolean;
}

function longDate(iso: string): string {
  const [year, month, day] = iso.split('-').map(Number);
  return new Date(year!, month! - 1, day!).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

function monthYear(iso: string): string {
  const [year, month] = iso.split('-').map(Number);
  return new Date(year!, month! - 1, 1).toLocaleDateString('en-GB', {
    month: 'long',
    year: 'numeric',
  });
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

/** What a goal card shows, from the API's computed fields. */
export function goalCard(goal: GoalRead): GoalCard {
  const emergency = goal.type === 'emergency_fund';
  const percent = Number(goal.percent);
  const notes: string[] = [];
  let pace: string;

  if (goal.target_amount === null) {
    pace = 'The target appears after your first complete month with expenses.';
  } else if (goal.reached) {
    pace = 'Target reached.';
  } else if (goal.overdue && goal.deadline) {
    pace = `The deadline (${longDate(goal.deadline)}) has passed: ${formatMoney(goal.remaining)} to go.`;
  } else if (goal.deadline && goal.per_month) {
    pace = `Save ${formatMoney(goal.per_month)} a month to reach it by ${monthYear(goal.deadline)}.`;
  } else {
    pace = `${formatMoney(goal.remaining)} to go, no deadline.`;
  }

  if (goal.deadline && !goal.reached && !goal.overdue && goal.months_left !== null) {
    notes.push(
      `${plural(goal.months_left, 'month')} left, this one included (${plural(goal.days_left ?? 0, 'day')})`,
    );
  }
  if (emergency && goal.months_of_expenses) {
    notes.push(
      goal.average_expenses
        ? `${plural(goal.months_of_expenses, 'month')} of ${formatMoney(goal.average_expenses)} average expenses`
        : `${plural(goal.months_of_expenses, 'month')} of expenses`,
    );
  }
  if (goal.manual_progress !== null) notes.push('Progress set by hand');

  return {
    id: goal.id,
    // "Emergency fund · Emergency Fund" would say it twice.
    title:
      emergency && goal.label_name.toLowerCase() !== 'emergency fund'
        ? `Emergency fund · ${goal.label_name}`
        : emergency
          ? 'Emergency fund'
          : goal.label_name,
    emergency,
    color: goal.color,
    icon: goal.icon,
    amounts:
      goal.target_amount === null
        ? formatMoney(goal.progress)
        : `${formatMoney(goal.progress)} of ${formatMoney(goal.target_amount)}`,
    percent: `${percent.toFixed(0)}%`,
    width: Math.min(Math.max(percent, 0), 100),
    pace,
    notes,
    overdue: goal.overdue,
    reached: goal.reached,
  };
}

/** "Completed on 3 November 2026" */
export function completedText(goal: GoalRead): string {
  return goal.completed_at ? `Completed on ${longDate(goal.completed_at.slice(0, 10))}` : '';
}
