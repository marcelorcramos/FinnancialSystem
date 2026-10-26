export const KINDS = ['expense', 'saving', 'investment'] as const;
export type Kind = (typeof KINDS)[number];

/** Material Symbols icon shown next to every value of a given kind. */
export const KIND_ICONS: Record<Kind, string> = {
  expense: 'receipt_long',
  saving: 'savings',
  investment: 'trending_up',
};
