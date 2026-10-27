import { Dialog } from '@angular/cdk/dialog';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { LabelRead } from '../../core/api/types';
import { ToastService } from '../../shared/ui/toast.service';
import { LabelsApi } from './labels-api';
import LabelsPage from './labels-page';

function label(name: string, kind: LabelRead['kind'], extra: Partial<LabelRead> = {}): LabelRead {
  return {
    id: name.toLowerCase(),
    name,
    kind,
    color: '#FFB74D',
    icon: 'x',
    is_default: true,
    archived_at: null,
    ...extra,
  };
}

const LABELS = [
  label('Food', 'expense'),
  label('Housing', 'expense'),
  label('Savings', 'saving'),
  label('Gym', 'expense', { is_default: false, archived_at: '2026-10-01T00:00:00Z' }),
];

describe('LabelsPage', () => {
  let fixture: ComponentFixture<LabelsPage>;
  let el: HTMLElement;
  let api: Record<string, ReturnType<typeof vi.fn>>;
  let dialog: { open: ReturnType<typeof vi.fn> };
  let toasts: ToastService;

  beforeEach(async () => {
    api = {
      list: vi.fn(() => of(LABELS)),
      archive: vi.fn(() => of({})),
      unarchive: vi.fn(() => of({})),
      restore: vi.fn(() => of({})),
      delete: vi.fn(() => of(undefined)),
    };
    dialog = { open: vi.fn() };
    TestBed.configureTestingModule({
      imports: [LabelsPage],
      providers: [
        { provide: LabelsApi, useValue: api },
        { provide: Dialog, useValue: dialog },
      ],
    });
    toasts = TestBed.inject(ToastService);
    fixture = TestBed.createComponent(LabelsPage);
    el = fixture.nativeElement;
    await fixture.whenStable();
  });

  const page = () => fixture.componentInstance as unknown as Record<string, (l: LabelRead) => void>;

  it('groups active labels by kind and lists archived ones apart', () => {
    const groups = [...el.querySelectorAll('.group')].map((group) => ({
      title: group.querySelector('h2')?.textContent?.replace(/\s+/g, ' ').trim(),
      names: [...group.querySelectorAll('.row__name')].map((n) =>
        n.firstChild?.textContent?.trim(),
      ),
    }));
    expect(groups).toEqual([
      { title: 'Expense 2', names: ['Food', 'Housing'] },
      { title: 'Saving 1', names: ['Savings'] },
      { title: 'Investment 0', names: [] },
    ]);
    expect(el.querySelector('.archived summary')?.textContent).toContain('Archived (1)');
  });

  it('archives a label and offers undo', () => {
    page()['archive'](LABELS[0]!);

    expect(api['archive']).toHaveBeenCalledWith('food');
    const toast = toasts.toasts()[0]!;
    expect(toast.message).toBe('“Food” archived');
    toasts.act(toast);
    expect(api['unarchive']).toHaveBeenCalledWith('food');
  });

  it('deletes a label without entries and offers undo', () => {
    page()['delete'](LABELS[1]!);

    expect(api['delete']).toHaveBeenCalledWith('housing');
    toasts.act(toasts.toasts()[0]!);
    expect(api['restore']).toHaveBeenCalledWith('housing');
  });

  it('asks where to move the entries when the label has some', () => {
    api['delete']!.mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 409 })));
    dialog.open.mockReturnValue({ closed: of({ action: 'reassign', targetId: 'housing' }) });

    page()['delete'](LABELS[0]!);

    const data = dialog.open.mock.calls[0]![1].data;
    expect(data.targets.map((l: LabelRead) => l.name)).toEqual(['Housing', 'Savings']);
    expect(api['delete']).toHaveBeenLastCalledWith('food', 'housing');
  });

  it('can archive instead of deleting', () => {
    api['delete']!.mockReturnValueOnce(throwError(() => new HttpErrorResponse({ status: 409 })));
    dialog.open.mockReturnValue({ closed: of({ action: 'archive' }) });

    page()['delete'](LABELS[0]!);
    expect(api['archive']).toHaveBeenCalledWith('food');
  });

  it('shows the API message when something fails', () => {
    api['archive']!.mockReturnValueOnce(
      throwError(() => new HttpErrorResponse({ status: 409, error: { detail: 'Month closed' } })),
    );
    page()['archive'](LABELS[0]!);
    expect(toasts.toasts()[0]?.message).toBe('Month closed');
  });
});
