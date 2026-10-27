import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Kind } from './kind';
import { MoneyAmount } from './money-amount';

describe('MoneyAmount', () => {
  let fixture: ComponentFixture<MoneyAmount>;
  let host: HTMLElement;

  async function render(amount: string, kind: Kind, showKind = true) {
    fixture.componentRef.setInput('amount', amount);
    fixture.componentRef.setInput('kind', kind);
    fixture.componentRef.setInput('showKind', showKind);
    await fixture.whenStable();
  }

  const text = (selector: string) => host.querySelector(selector)?.textContent?.trim();

  beforeEach(() => {
    fixture = TestBed.createComponent(MoneyAmount);
    host = fixture.nativeElement;
  });

  it.each<[Kind, string]>([
    ['expense', 'Expense'],
    ['saving', 'Saving'],
    ['investment', 'Investment'],
  ])('renders %s with colour hook, icon and text', async (kind, label) => {
    await render('212.00', kind);

    expect(host.getAttribute('data-kind')).toBe(kind);
    expect(host.querySelector('.money-amount__icon svg')?.getAttribute('aria-hidden')).toBe('true');
    expect(text('.money-amount__value')).toBe('€212.00');
    expect(text('.money-amount__kind')).toBe(label);
  });

  it('keeps the kind text for screen readers when hidden visually', async () => {
    await render('10', 'saving', false);

    const kind = host.querySelector('.money-amount__kind');
    expect(kind?.classList).toContain('visually-hidden');
    expect(kind?.textContent?.trim()).toBe('Saving');
  });
});
