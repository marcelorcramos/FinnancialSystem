import { TestBed } from '@angular/core/testing';

import { ToastService } from './toast.service';

describe('ToastService', () => {
  let service: ToastService;

  beforeEach(() => {
    vi.useFakeTimers();
    service = TestBed.inject(ToastService);
  });

  afterEach(() => vi.useRealTimers());

  it('shows a toast and hides it after a while', () => {
    service.show('Label deleted');
    expect(service.toasts().map((t) => t.message)).toEqual(['Label deleted']);

    vi.advanceTimersByTime(6000);
    expect(service.toasts()).toEqual([]);
  });

  it('runs the action and closes the toast', () => {
    const run = vi.fn();
    service.show('Label deleted', { label: 'Undo', run });

    service.act(service.toasts()[0]!);
    expect(run).toHaveBeenCalled();
    expect(service.toasts()).toEqual([]);
  });

  it('runs the newest Undo on demand', () => {
    const service = TestBed.inject(ToastService);
    const first = vi.fn();
    const second = vi.fn();
    expect(service.undoLatest()).toBe(false);
    service.show('A deleted', { label: 'Undo', run: first });
    service.show('B deleted', { label: 'Undo', run: second });
    service.show('Saved');

    expect(service.undoLatest()).toBe(true);
    expect(second).toHaveBeenCalledOnce();
    expect(first).not.toHaveBeenCalled();
    expect(service.toasts().map((t) => t.message)).toEqual(['A deleted', 'Saved']);
  });
});
