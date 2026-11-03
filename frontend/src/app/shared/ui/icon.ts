import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

/** Stroke icons drawn on a 24×24 grid. Each entry is one or more SVG path definitions. */
const ICONS = {
  logo: [
    'M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z',
    'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
    'M12 7V4M12 20v-3M7 12H4M20 12h-3',
  ],
  month: [
    'M7 3v3M17 3v3M4 9h16',
    'M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z',
  ],
  reports: ['M3 21h18', 'M6 17v-6M11 17V5M16 17v-9M21 17v-3'],
  labels: ['M3 12V4h8l9 9-8 8-9-9z', 'M7.5 7.5h.01'],
  user: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4 21a8 8 0 0 1 16 0'],
  bell: ['M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9', 'M10.3 21a1.94 1.94 0 0 0 3.4 0'],
  target: [
    'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
    'M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12z',
    'M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  ],
  gauge: ['M12 14l4-4', 'M3.34 19a10 10 0 1 1 17.32 0'],
  logout: ['M9 21H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h4', 'M16 17l5-5-5-5M21 12H9'],
  eye: ['M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
  'eye-off': [
    'M3 3l18 18',
    'M10.6 5.1A10 10 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4.2M6.6 6.6A17 17 0 0 0 2 12s3.5 7 10 7a9.6 9.6 0 0 0 5.4-1.6',
    'M9.9 9.9a3 3 0 0 0 4.2 4.2',
  ],
  plus: ['M12 5v14M5 12h14'],
  transfer: ['M4 7h16l-4-4', 'M20 17H4l4 4'],
  'chevron-left': ['M15 6l-6 6 6 6'],
  'chevron-right': ['M9 6l6 6-6 6'],
  'chevron-down': ['M6 9l6 6 6-6'],
  close: ['M6 6l12 12M18 6L6 18'],
  check: ['M5 12l5 5 9-10'],
  alert: [
    'M12 9v4M12 17h.01',
    'M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
  ],
  info: ['M12 11v6M12 7h.01', 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z'],
  sun: [
    'M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z',
    'M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  ],
  moon: ['M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
  contrast: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 2v20'],
  expense: ['M6 3h12v18l-3-2-3 2-3-2-3 2V3z', 'M9 8h6M9 12h6'],
  saving: ['M5 8h14v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8z', 'M8 8V5h8v3', 'M12 12v5M10 14.5h4'],
  investment: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  edit: ['M4 20h4L19 9l-4-4L4 16v4z'],
  archive: ['M3 4h18v4H3z', 'M5 8v12h14V8M10 12h4'],
  trash: ['M4 7h16M10 11v6M14 11v6', 'M6 7l1 13h10l1-13M9 7V4h6v3'],
  menu: ['M4 6h16M4 12h16M4 18h16'],
  sliders: ['M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3', 'M1 14h6M9 8h6M17 16h6'],

  // Label icons. Names match what the backend stores in labels.icon.
  restaurant: ['M7 3v8a2 2 0 0 0 4 0V3M9 11v10', 'M17 3c-2 0-3 2-3 6h3v12'],
  home: ['M3 11l9-7 9 7', 'M5 10v10h14V10', 'M10 20v-6h4v6'],
  bolt: ['M13 2L4 14h7l-1 8 9-12h-7z'],
  water_drop: ['M12 3s7 7.5 7 12a7 7 0 0 1-14 0c0-4.5 7-12 7-12z'],
  directions_bus: [
    'M6 3h12a2 2 0 0 1 2 2v12H4V5a2 2 0 0 1 2-2z',
    'M4 11h16M7 21v-4M17 21v-4M8 14h.01M16 14h.01',
  ],
  medical_services: ['M4 8h16v12H4z', 'M9 8V5h6v3M12 11v6M9 14h6'],
  wifi: ['M2 9a15 15 0 0 1 20 0M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0', 'M12 19.5h.01'],
  subscriptions: ['M3 6h18v13H3z', 'M6 3h12', 'M10 10v6l5-3-5-3z'],
  savings: ['M5 8h14v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8z', 'M8 8V5h8v3', 'M12 12v5M10 14.5h4'],
  health_and_safety: ['M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z', 'M12 9v6M9 12h6'],
  trending_up: ['M3 17l6-6 4 4 8-8', 'M15 7h6v6'],
  shopping_cart: ['M3 4h2l2.4 11h10.2L20 8H7', 'M10 20h.01M17 20h.01'],
  fitness_center: ['M6 7v10M18 7v10M3 10v4M21 10v4M6 12h12'],
  flight: ['M2 16l20-8-8 14-2-6z'],
  menu_book: ['M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5z', 'M8 7h7'],
  pets: [
    'M12 13c-3 0-5 3-5 5 0 1.5 1.5 2 2.5 1.5S11 19 12 19s1.5 1 2.5.5S17 19.5 17 18c0-2-2-5-5-5z',
    'M5 9h.01M9 5h.01M15 5h.01M19 9h.01',
  ],
  school: ['M2 9l10-5 10 5-10 5-10-5z', 'M6 11v5c3 2 9 2 12 0v-5'],
  redeem: [
    'M3 9h18v4H3z',
    'M5 13v8h14v-8M12 9v12',
    'M12 9C10 6 7 6 7 8s3 1 5 1c2 0 5 1 5-1s-3-2-5 1',
  ],
  work: ['M3 7h18v13H3z', 'M8 7V4h8v3M3 12h18'],
} as const satisfies Record<string, readonly string[]>;

export type IconName = keyof typeof ICONS;

/** Icons a user can pick for a label, in picker order. */
export const LABEL_ICONS: readonly IconName[] = [
  'restaurant',
  'shopping_cart',
  'home',
  'bolt',
  'water_drop',
  'directions_bus',
  'medical_services',
  'wifi',
  'subscriptions',
  'fitness_center',
  'flight',
  'menu_book',
  'school',
  'pets',
  'redeem',
  'work',
  'savings',
  'health_and_safety',
  'trending_up',
];

export function isIconName(value: string): value is IconName {
  return Object.hasOwn(ICONS, value);
}

/**
 * An icon from the Vault set. Decorative by default (hidden from screen
 * readers); pass `label` when the icon carries meaning on its own.
 */
@Component({
  selector: 'app-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'icon' },
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      [attr.role]="label() ? 'img' : null"
      [attr.aria-label]="label() || null"
      [attr.aria-hidden]="label() ? null : 'true'"
    >
      @for (d of paths(); track $index) {
        <path [attr.d]="d" />
      }
    </svg>
  `,
  styles: `
    :host {
      display: inline-flex;
      flex-shrink: 0;
    }
  `,
})
export class Icon {
  readonly name = input.required<IconName>();
  readonly size = input(20);
  readonly label = input<string>();

  protected readonly paths = computed(() => ICONS[this.name()]);
}
