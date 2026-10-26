import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslocoService } from '@jsverse/transloco';

import { provideTestI18n } from '../../../testing/i18n';
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

  const text = (selector: string) =>
    host.querySelector(selector)?.textContent?.replace(/[\u00a0\u202f]/g, ' ').trim();

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [MoneyAmount, provideTestI18n()] });
    fixture = TestBed.createComponent(MoneyAmount);
    host = fixture.nativeElement;
  });

  it.each<[Kind, string, string]>([
    ['expense', 'receipt_long', 'Gasto'],
    ['saving', 'savings', 'Poupança'],
    ['investment', 'trending_up', 'Investimento'],
  ])('renders %s with colour hook, icon and text', async (kind, icon, label) => {
    await render('212.00', kind);

    expect(host.getAttribute('data-kind')).toBe(kind);
    expect(text('.money-amount__icon')).toBe(icon);
    expect(host.querySelector('.money-amount__icon')?.getAttribute('aria-hidden')).toBe('true');
    expect(text('.money-amount__value')).toBe('212,00 €');
    expect(text('.money-amount__kind')).toBe(label);
  });

  it('keeps the kind text for screen readers when hidden visually', async () => {
    await render('10', 'saving', false);

    const kind = host.querySelector('.money-amount__kind');
    expect(kind?.classList).toContain('cdk-visually-hidden');
    expect(kind?.textContent?.trim()).toBe('Poupança');
  });

  it('translates the kind text with the active language', async () => {
    TestBed.inject(TranslocoService).setActiveLang('en');
    await render('10', 'investment');

    expect(text('.money-amount__kind')).toBe('Investment');
  });
});
