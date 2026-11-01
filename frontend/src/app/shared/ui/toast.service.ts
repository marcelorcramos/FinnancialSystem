import { Injectable, signal } from '@angular/core';

export interface ToastAction {
  label: string;
  run: () => void;
}

export interface Toast {
  id: number;
  message: string;
  action?: ToastAction;
}

const DURATION_MS = 6000;

/** Short messages at the bottom of the screen, optionally with one action (e.g. Undo). */
@Injectable({ providedIn: 'root' })
export class ToastService {
  private nextId = 1;
  private readonly _toasts = signal<Toast[]>([]);
  readonly toasts = this._toasts.asReadonly();

  show(message: string, action?: ToastAction): void {
    const toast: Toast = { id: this.nextId++, message, action };
    this._toasts.update((list) => [...list, toast]);
    setTimeout(() => this.dismiss(toast.id), DURATION_MS);
  }

  dismiss(id: number): void {
    this._toasts.update((list) => list.filter((toast) => toast.id !== id));
  }

  /** Runs the toast's action and closes it. */
  act(toast: Toast): void {
    this.dismiss(toast.id);
    toast.action?.run();
  }

  /** Runs the newest Undo still on screen (⌘/Ctrl+Z). Returns whether there was one. */
  undoLatest(): boolean {
    const toast = this._toasts()
      .filter((t) => t.action?.label === 'Undo')
      .at(-1);
    if (!toast) return false;
    this.act(toast);
    return true;
  }
}
