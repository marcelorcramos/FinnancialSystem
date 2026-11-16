import { IconName } from '../../shared/ui/icon';

export interface NavItem {
  path: string;
  label: string;
  icon: IconName;
  exact?: boolean;
}

/** Main navigation. Features add their entries here as they land. */
export const NAV_ITEMS: NavItem[] = [
  { path: '/month', label: 'Month', icon: 'month' },
  { path: '/reports', label: 'Reports', icon: 'reports' },
  { path: '/goals', label: 'Goals', icon: 'target' },
  { path: '/labels', label: 'Labels', icon: 'labels' },
];

/** Shown only when the server has the assistant set up. */
export const ASSISTANT_NAV_ITEM: NavItem = { path: '/assistant', label: 'Assistant', icon: 'chat' };
