import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

export interface DonutSegment {
  key: string;
  label: string;
  /** Used only to size the slice; the text shown is `display`. */
  value: number;
  /** Any CSS colour, e.g. `var(--kind-expense)`. */
  color: string;
  /** Formatted value, e.g. "€212.00". */
  display: string;
}

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
            <span class="legend__dot" [style.background]="item.color" aria-hidden="true"></span>
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

  protected readonly arcs = computed(() => {
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
