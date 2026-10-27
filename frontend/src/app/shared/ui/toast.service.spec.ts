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
});
