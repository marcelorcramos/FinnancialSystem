import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';

import { DisplayPreferencesService } from '../../core/preferences/display-preferences';

export interface DonutSegment {
  key: string;
  label: string;
  /** Used only to size the slice; the text shown is `display`. */
  value: number;
  /** Any CSS colour, e.g. `var(--kind-expense)`. */
  color: string;
  /** Formatted value, e.g. "€212.00". */
  display: string;
  /** Texture drawn over the colour when "Patterns in charts" is on. */
  pattern?: 'lines' | 'dots';
}

let nextId = 0;

const RADIUS = 100;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 6;

/**
 * Thick donut with a centre readout. Hovering a slice, or hovering/focusing its
 * legend entry, highlights it and shows its value in the centre. The legend
 * lists every value as text, so the chart never relies on colour alone.
 */
@Component({
  selector: 'app-donut',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 280 280" class="donut" role="img" [attr.aria-label]="ariaLabel()">
      <defs>
        <pattern
          [attr.id]="ids.lines"
          width="8"
          height="8"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line x1="0" y1="0" x2="0" y2="8" class="ink" stroke-width="2.5" />
        </pattern>
        <pattern [attr.id]="ids.dots" width="8" height="8" patternUnits="userSpaceOnUse">
          <circle cx="4" cy="4" r="1.6" class="ink" />
        </pattern>
      </defs>
      <g transform="rotate(-90 140 140)" fill="none">
        <circle cx="140" cy="140" r="100" class="track" stroke-width="44" />
        @for (arc of arcs(); track arc.key) {
          <circle
            cx="140"
            cy="140"
            r="100"
            class="arc"
            [style.stroke]="arc.color"
            [attr.stroke-width]="arc.width"
            [attr.opacity]="arc.opacity"
            [attr.stroke-dasharray]="arc.dash"
            [attr.stroke-dashoffset]="arc.offset"
            (mouseenter)="active.set(arc.key)"
            (mouseleave)="active.set(null)"
          />
          @if (arc.pattern) {
            <circle
              cx="140"
              cy="140"
              r="100"
              class="arc arc--pattern"
              [style.stroke]="'url(#' + arc.pattern + ')'"
              [attr.stroke-width]="arc.width"
              [attr.opacity]="arc.opacity"
              [attr.stroke-dasharray]="arc.dash"
              [attr.stroke-dashoffset]="arc.offset"
            />
          }
        }
      </g>
      <text x="140" y="122" text-anchor="middle" class="center__label">{{ center().label }}</text>
      <text x="140" y="156" text-anchor="middle" class="center__value">{{ center().value }}</text>
      <text x="140" y="180" text-anchor="middle" class="center__hint">{{ center().hint }}</text>
    </svg>
    <ul class="legend">
      @for (item of legend(); track item.key) {
        <li>
          <button
            type="button"
            class="legend__item"
            (mouseenter)="active.set(item.key)"
            (mouseleave)="active.set(null)"
            (focus)="active.set(item.key)"
            (blur)="active.set(null)"
          >
            <span
              class="legend__dot"
              [style.background-color]="item.color"
              [attr.data-pattern]="display.current().patterns ? item.pattern : null"
              aria-hidden="true"
            ></span>
            <span>{{ item.label }}</span
            >{{ ' ' }}<span class="legend__share">{{ item.share }}</span>
          </button>
        </li>
      }
    </ul>
  `,
  styleUrl: './donut.scss',
})
export class Donut {
  readonly segments = input.required<DonutSegment[]>();
  readonly centerLabel = input('TOTAL');
  readonly centerValue = input('');
  readonly centerHint = input('');

  protected readonly active = signal<string | null>(null);

  private readonly total = computed(() =>
    this.segments().reduce((sum, s) => sum + Math.max(s.value, 0), 0),
  );

  private share(segment: DonutSegment): string {
    const total = this.total();
    return total > 0 ? `${((Math.max(segment.value, 0) / total) * 100).toFixed(1)}%` : '0.0%';
  }

  protected readonly display = inject(DisplayPreferencesService);
  protected readonly ids = { lines: `donut-lines-${nextId}`, dots: `donut-dots-${nextId++}` };

  protected readonly arcs = computed(() => {
    const patterns = this.display.current().patterns;
    const total = this.total();
    const visible = this.segments().filter((s) => s.value > 0);
    const gap = visible.length > 1 ? GAP : 0;
    const active = this.active();
    let cursor = 0;
    return visible.map((segment) => {
      const length = (segment.value / total) * CIRCUMFERENCE;
      const arc = {
        key: segment.key,
        color: segment.color,
        width: active === segment.key ? 56 : 44,
        opacity: active && active !== segment.key ? 0.3 : 1,
        dash: `${Math.max(length - gap, 0.01).toFixed(2)} ${CIRCUMFERENCE.toFixed(2)}`,
        offset: (-cursor).toFixed(2),
        pattern: patterns && segment.pattern ? this.ids[segment.pattern] : null,
      };
      cursor += length;
      return arc;
    });
  });

  protected readonly legend = computed(() =>
    this.segments().map((segment) => ({ ...segment, share: this.share(segment) })),
  );

  protected readonly center = computed(() => {
    const segment = this.segments().find((s) => s.key === this.active());
    if (!segment) {
      return { label: this.centerLabel(), value: this.centerValue(), hint: this.centerHint() };
    }
    return {
      label: segment.label.toUpperCase(),
      value: segment.display,
      hint: this.share(segment),
    };
  });

  protected readonly ariaLabel = computed(() =>
    this.segments()
      .map((s) => `${s.label} ${s.display}, ${this.share(s)}`)
      .join('; '),
  );
}
