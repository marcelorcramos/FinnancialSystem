import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { LabelRead } from '../../core/api/types';
import { LabelEditorData, LabelEditorDialog } from './label-editor-dialog';
import { LabelsApi } from './labels-api';

const SUGGESTIONS = [
  '#EF5350',
  '#EC407A',
  '#AB47BC',
  '#7E57C2',
  '#5C6BC0',
  '#29B6F6',
  '#26C6DA',
  '#9CCC65',
];
const FOOD: LabelRead = {
  id: 'food',
  name: 'Food',
  kind: 'expense',
  color: '#FFB74D',
  icon: 'restaurant',
  is_default: true,
  archived_at: null,
};

describe('LabelEditorDialog', () => {
  let fixture: ComponentFixture<LabelEditorDialog>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let close: ReturnType<typeof vi.fn>;

  async function render(data: LabelEditorData = {}) {
    api = {
      colorSuggestions: vi.fn(() => of(SUGGESTIONS)),
      create: vi.fn((body) => of({ ...FOOD, ...body, id: 'new' })),
      update: vi.fn((id, body) => of({ ...FOOD, ...body })),
    };
    close = vi.fn();
    TestBed.configureTestingModule({
      imports: [LabelEditorDialog],
      providers: [
        { provide: LabelsApi, useValue: api },
        { provide: DialogRef, useValue: { close } },
        { provide: DIALOG_DATA, useValue: data },
      ],
    });
    fixture = TestBed.createComponent(LabelEditorDialog);
    el = fixture.nativeElement;
    await fixture.whenStable();
  }

  function type(selector: string, value: string) {
    const input = el.querySelector<HTMLInputElement>(selector)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }

  /** A radio by its kind name or its aria-label. */
  function radio(name: string): HTMLInputElement {
    const byLabel = el.querySelector<HTMLInputElement>(`input[aria-label="${name}"]`);
    if (byLabel) return byLabel;
    const choice = [...el.querySelectorAll('.choice')].find((c) => c.textContent?.includes(name))!;
    return choice.querySelector('input')!;
  }

  async function submit() {
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    await fixture.whenStable();
  }

  it('offers the 8 free colors and picks the first one', async () => {
    await render();
    const swatches = [...el.querySelectorAll<HTMLInputElement>('.swatch input')];
    expect(swatches.map((s) => s.getAttribute('aria-label'))).toEqual(
      SUGGESTIONS.map((c) => `Color ${c}`),
    );
    expect(swatches[0]!.checked).toBe(true);
    expect(el.querySelector<HTMLInputElement>('#label-color')!.value).toBe('#EF5350');
  });

  it('creates a label with a custom color', async () => {
    await render();
    type('#label-name', ' Gym ');
    radio('Saving').click();
    type('#label-color', '#ab47bc');
    radio('fitness center').click();
    await submit();

    expect(api['create']).toHaveBeenCalledWith({
      name: 'Gym',
      kind: 'saving',
      color: '#AB47BC',
      icon: 'fitness_center',
    });
    expect(close).toHaveBeenCalledWith(expect.objectContaining({ id: 'new' }));
  });

  it('validates the name and the color format', async () => {
    await render();
    type('#label-color', 'red');
    await submit();

    expect(api['create']).not.toHaveBeenCalled();
    const errors = [...el.querySelectorAll('.field__error')].map((e) => e.textContent?.trim());
    expect(errors).toEqual(['This field is required.', 'Use the #RRGGBB format, e.g. #AB47BC.']);
  });

  it('edits a label, keeping its color first and warning when the kind changes', async () => {
    await render({ label: FOOD });
    expect(el.querySelector('h2')?.textContent).toContain('Edit label');
    expect(el.querySelector('.swatch input')!.getAttribute('aria-label')).toBe('Color #FFB74D');
    expect(el.querySelector('.warning')).toBeNull();

    radio('Investment').click();
    await fixture.whenStable();
    expect(el.querySelector('.warning')?.textContent).toContain('past reports');

    await submit();
    expect(api['update']).toHaveBeenCalledWith(
      'food',
      expect.objectContaining({ kind: 'investment' }),
    );
  });

  it('shows the API message when the name or color is taken', async () => {
    await render();
    api['create']!.mockReturnValueOnce(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 409,
            error: { detail: "A label named 'Gym' already exists" },
          }),
      ),
    );
    type('#label-name', 'Gym');
    await submit();

    expect(el.querySelector('[role=alert]')?.textContent).toContain('already exists');
    expect(close).not.toHaveBeenCalled();
  });
});
