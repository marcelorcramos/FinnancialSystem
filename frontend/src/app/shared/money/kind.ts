import { IconName } from '../ui/icon';

export const KINDS = ['expense', 'saving', 'investment'] as const;
export type Kind = (typeof KINDS)[number];

export const KIND_NAMES: Record<Kind, string> = {
  expense: 'Expense',
  saving: 'Saving',
  investment: 'Investment',
};

/** Icon shown next to every value of a given kind. */
export const KIND_ICONS: Record<Kind, IconName> = {
  expense: 'expense',
  saving: 'saving',
  investment: 'investment',
};
