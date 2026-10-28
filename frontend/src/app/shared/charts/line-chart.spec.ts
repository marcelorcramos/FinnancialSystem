import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LineChart, LinePoint, niceCeil } from './line-chart';

function points(values: number[]): LinePoint[] {
  return values.map((value, i) => ({
    key: `m${i}`,
    label: `M${i + 1}`,
    value,
    display: `€${value.toFixed(2)}`,
  }));
}

describe('niceCeil', () => {
  it('rounds up to 1, 2 or 5 times a power of ten', () => {
    expect([0, 0.4, 3, 7, 230, 260, 900].map(niceCeil)).toEqual([0, 0.5, 5, 10, 500, 500, 1000]);
  });
});

describe('LineChart', () => {
  let fixture: ComponentFixture<LineChart>;
  let el: HTMLElement;

  async function render(values: number[]) {
    fixture = TestBed.createComponent(LineChart);
    fixture.componentRef.setInput('points', points(values));
    fixture.componentRef.setInput('ariaLabel', 'Food over 3 months');
    fixture.componentRef.setInput('formatAxis', (v: number) => `€${v}`);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  const axis = () =>
    [...el.querySelectorAll('.axis:not(.axis--x)')].map((t) => t.textContent?.trim());

  it('draws one point per value with a readable axis from zero', async () => {
    await render([200, 230, 212]);
    expect(el.querySelector('svg')?.getAttribute('aria-label')).toBe('Food over 3 months');
    expect(el.querySelectorAll('circle.dot').length).toBe(3);
    expect(axis()).toEqual(['€500', '€250', '€0']);
    expect([...el.querySelectorAll('.axis--x')].map((t) => t.textContent?.trim())).toEqual([
      'M1',
      'M2',
      'M3',
    ]);
    expect(el.querySelector('.line')?.getAttribute('d')).toMatch(/^M\S+ \S+ L\S+ \S+ L\S+ \S+$/);
  });

  it('shows the value of a hovered or focused point', async () => {
    await render([200, 230, 212]);
    const dot = el.querySelectorAll<SVGCircleElement>('circle.dot')[1]!;
    expect(dot.getAttribute('aria-label')).toBe('M2: €230.00');
    dot.dispatchEvent(new Event('focus'));
    await fixture.whenStable();
    expect(el.querySelector('.tip text')?.textContent).toBe('€230.00');
    expect(dot.getAttribute('r')).toBe('10');
    dot.dispatchEvent(new Event('blur'));
    await fixture.whenStable();
    expect(el.querySelector('.tip')).toBeNull();
  });

  it('keeps zero on the axis when money moved out', async () => {
    await render([30, -40]);
    expect(axis()).toEqual(['€50', '€0', '€-50']);
  });

  it('thins the month labels of a long series but keeps the newest', async () => {
    await render(Array.from({ length: 24 }, (_, i) => i));
    const labels = [...el.querySelectorAll('.axis--x')].map((t) => t.textContent?.trim());
    expect(labels.length).toBe(12);
    expect(labels.at(-1)).toBe('M24');
  });
});
