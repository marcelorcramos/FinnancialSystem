import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

export interface LinePoint {
  key: string;
  /** Axis text, e.g. "May". */
  label: string;
  /** Used only to place the point; the text shown is `display`. */
  value: number;
  /** Formatted value, e.g. "€212.00". */
  display: string;
}

const WIDTH = 900;
const LEFT = 76;
const RIGHT = 860;
const TOP = 40;
const BOTTOM = 240;
/** At most this many axis labels; longer series show every n-th one. */
const MAX_LABELS = 12;

/** A round number at or above `value` (1, 2 or 5 times a power of ten). */
export function niceCeil(value: number): number {
  if (value <= 0) return 0;
  const power = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((m) => m * power >= value)!;
  return step * power;
}

/**
 * Line with a soft area over months. Points grow on hover or keyboard focus and
 * show their value; the chart's label reads every value, so the chart never
 * relies on the drawing alone.
 */
@Component({
  selector: 'app-line-chart',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.viewBox]="'0 0 ' + width + ' 300'"
      class="chart"
      role="img"
      [attr.aria-label]="ariaLabel()"
    >
      @for (tick of ticks(); track tick.y) {
        <line
          [attr.x1]="left"
          [attr.x2]="right"
          [attr.y1]="tick.y"
          [attr.y2]="tick.y"
          [class.grid--base]="tick.base"
          class="grid"
        />
        <text [attr.x]="left - 12" [attr.y]="tick.y + 4" text-anchor="end" class="axis">
          {{ tick.text }}
        </text>
      }
      @if (shape(); as s) {
        <path [attr.d]="s.area" class="area" [style.fill]="color()" />
        <path [attr.d]="s.line" class="line" [style.stroke]="color()" />
      }
      @for (point of placed(); track point.key; let last = $last) {
        @if (point.showLabel) {
          <text
            [attr.x]="point.x"
            y="272"
            text-anchor="middle"
            class="axis axis--x"
            [class.axis--current]="last"
          >
            {{ point.label }}
          </text>
        }
        <circle
          class="dot"
          tabindex="0"
          [attr.cx]="point.x"
          [attr.cy]="point.y"
          [attr.r]="active() === point.key ? 10 : 7"
          [style.stroke]="color()"
          [style.fill]="last ? color() : null"
          [attr.aria-label]="point.label + ': ' + point.display"
          (mouseenter)="active.set(point.key)"
          (mouseleave)="active.set(null)"
          (focus)="active.set(point.key)"
          (blur)="active.set(null)"
        />
      }
      @if (tip(); as t) {
        <g class="tip" [attr.transform]="'translate(' + t.x + ' ' + t.y + ')'">
          <rect [attr.x]="-t.width / 2" y="-50" [attr.width]="t.width" height="34" rx="4" />
          <text x="0" y="-28" text-anchor="middle">{{ t.text }}</text>
        </g>
      }
    </svg>
  `,
  styleUrl: './line-chart.scss',
})
export class LineChart {
  readonly points = input.required<LinePoint[]>();
  /** Any CSS colour, e.g. the label's colour. */
  readonly color = input('var(--color-accent)');
  readonly ariaLabel = input('');
  /** Axis text for a value, e.g. whole euros. */
  readonly formatAxis = input<(value: number) => string>((value) => String(value));

  protected readonly width = WIDTH;
  protected readonly left = LEFT;
  protected readonly right = RIGHT;
  protected readonly active = signal<string | null>(null);

  /** The value range, always including zero, rounded to a readable top. */
  private readonly range = computed(() => {
    const values = this.points().map((p) => p.value);
    const high = niceCeil(Math.max(...values, 0) * 1.15) || 1;
    const low = -niceCeil(-Math.min(...values, 0) * 1.15);
    return { low, high };
  });

  private y(value: number): number {
    const { low, high } = this.range();
    return BOTTOM - ((value - low) / (high - low)) * (BOTTOM - TOP);
  }

  protected readonly ticks = computed(() => {
    const { low, high } = this.range();
    const format = this.formatAxis();
    const values = low < 0 ? [high, 0, low] : [high, high / 2, 0];
    return values.map((value) => ({
      y: Number(this.y(value).toFixed(1)),
      text: format(value),
      base: value === 0,
    }));
  });

  protected readonly placed = computed(() => {
    const points = this.points();
    const every = Math.ceil(points.length / MAX_LABELS);
    const span = points.length > 1 ? (RIGHT - LEFT - 40) / (points.length - 1) : 0;
    return points.map((point, i) => ({
      ...point,
      x: Number((points.length > 1 ? LEFT + 20 + i * span : (LEFT + RIGHT) / 2).toFixed(1)),
      y: Number(this.y(point.value).toFixed(1)),
      // The newest point always keeps its label.
      showLabel: (points.length - 1 - i) % every === 0,
    }));
  });

  protected readonly shape = computed(() => {
    const placed = this.placed();
    if (!placed.length) return null;
    const line = placed.map((p, i) => `${i ? 'L' : 'M'}${p.x} ${p.y}`).join(' ');
    const base = Number(this.y(0).toFixed(1));
    const first = placed[0]!;
    const last = placed.at(-1)!;
    return { line, area: `${line} L${last.x} ${base} L${first.x} ${base} Z` };
  });

  protected readonly tip = computed(() => {
    const point = this.placed().find((p) => p.key === this.active());
    if (!point) return null;
    const width = Math.max(96, point.display.length * 10 + 24);
    const x = Math.min(Math.max(point.x, LEFT + width / 2), WIDTH - width / 2);
    return { x, y: point.y, width, text: point.display };
  });
}
