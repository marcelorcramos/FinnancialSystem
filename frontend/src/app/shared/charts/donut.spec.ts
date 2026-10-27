import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Donut, DonutSegment } from './donut';

const SEGMENTS: DonutSegment[] = [
  { key: 'expense', label: 'Spent', value: 212, color: 'red', display: '€212.00' },
  { key: 'saving', label: 'Saved', value: 288, color: 'green', display: '€288.00' },
  { key: 'investment', label: 'Invested', value: 0, color: 'blue', display: '€0.00' },
];

describe('Donut', () => {
  let fixture: ComponentFixture<Donut>;
  let el: HTMLElement;

  beforeEach(async () => {
    fixture = TestBed.createComponent(Donut);
    fixture.componentRef.setInput('segments', SEGMENTS);
    fixture.componentRef.setInput('centerLabel', 'DISTRIBUTED');
    fixture.componentRef.setInput('centerValue', '€500.00');
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  const centre = () => [...el.querySelectorAll('text')].map((t) => t.textContent?.trim());

  it('draws one slice per non-zero value and a legend for every value', () => {
    expect(el.querySelectorAll('circle.arc').length).toBe(2);
    const legend = [...el.querySelectorAll('.legend__item')].map((b) =>
      b.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(legend).toEqual(['Spent 42.4%', 'Saved 57.6%', 'Invested 0.0%']);
  });

  it('describes every slice for screen readers', () => {
    expect(el.querySelector('svg')?.getAttribute('aria-label')).toBe(
      'Spent €212.00, 42.4%; Saved €288.00, 57.6%; Invested €0.00, 0.0%',
    );
  });

  it('shows the total in the centre until a slice is highlighted', async () => {
    expect(centre()).toEqual(['DISTRIBUTED', '€500.00', '']);

    el.querySelector<HTMLButtonElement>('.legend__item')!.dispatchEvent(new Event('focus'));
    await fixture.whenStable();
    expect(centre()).toEqual(['SPENT', '€212.00', '42.4%']);
    const arcs = [...el.querySelectorAll('circle.arc')];
    expect(arcs.map((a) => a.getAttribute('stroke-width'))).toEqual(['56', '44']);
    expect(arcs[1]!.getAttribute('opacity')).toBe('0.3');
  });
});
