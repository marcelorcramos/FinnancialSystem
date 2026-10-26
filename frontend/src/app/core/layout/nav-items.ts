export interface NavItem {
  path: string;
  /** Translation key. */
  label: string;
  icon: string;
  exact?: boolean;
}

/** Main navigation. Features add their entries here as they land. */
export const NAV_ITEMS: NavItem[] = [{ path: '/', label: 'nav.home', icon: 'home', exact: true }];
