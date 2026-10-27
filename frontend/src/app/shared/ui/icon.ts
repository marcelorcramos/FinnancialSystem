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
} as const satisfies Record<string, readonly string[]>;

export type IconName = keyof typeof ICONS;

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
