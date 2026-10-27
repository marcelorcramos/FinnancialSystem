import { IconName } from '../../shared/ui/icon';

export interface NavItem {
  path: string;
  label: string;
  icon: IconName;
  exact?: boolean;
}

/** Main navigation. Features add their entries here as they land. */
export const NAV_ITEMS: NavItem[] = [{ path: '/', label: 'Month', icon: 'month', exact: true }];
