import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Icon } from './icon';

describe('Icon', () => {
  let fixture: ComponentFixture<Icon>;
  let host: HTMLElement;

  beforeEach(() => {
    fixture = TestBed.createComponent(Icon);
    host = fixture.nativeElement;
  });

  const svg = () => host.querySelector('svg')!;

  it('draws the paths of the named icon and is hidden from screen readers', async () => {
    fixture.componentRef.setInput('name', 'eye');
    await fixture.whenStable();

    expect(svg().querySelectorAll('path').length).toBe(2);
    expect(svg().getAttribute('aria-hidden')).toBe('true');
    expect(svg().getAttribute('role')).toBeNull();
    expect(svg().getAttribute('width')).toBe('20');
  });

  it('becomes an image with a name when it has a label', async () => {
    fixture.componentRef.setInput('name', 'alert');
    fixture.componentRef.setInput('label', 'Warning');
    fixture.componentRef.setInput('size', 16);
    await fixture.whenStable();

    expect(svg().getAttribute('role')).toBe('img');
    expect(svg().getAttribute('aria-label')).toBe('Warning');
    expect(svg().getAttribute('aria-hidden')).toBeNull();
    expect(svg().getAttribute('width')).toBe('16');
  });
});
