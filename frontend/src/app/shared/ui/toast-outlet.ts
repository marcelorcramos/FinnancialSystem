import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { Icon } from './icon';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-toast-outlet',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="toasts" role="status" aria-live="polite">
      @for (toast of service.toasts(); track toast.id) {
        <div class="toast">
          <span class="toast__message">{{ toast.message }}</span>
          @if (toast.action; as action) {
            <button type="button" class="toast__action" (click)="service.act(toast)">
              {{ action.label }}
            </button>
          }
          <button
            type="button"
            class="toast__close"
            aria-label="Dismiss"
            (click)="service.dismiss(toast.id)"
          >
            <app-icon name="close" [size]="16" />
          </button>
        </div>
      }
    </div>
  `,
  styles: `
    .toasts {
      position: fixed;
      inset-inline: var(--space-4);
      bottom: var(--space-5);
      z-index: 1100;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--space-2);
      pointer-events: none;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      max-width: 520px;
      padding: var(--space-2) var(--space-2) var(--space-2) var(--space-4);
      border: 1px solid var(--color-border-strong);
      border-radius: var(--radius-m);
      background: var(--color-text);
      color: var(--color-bg);
      pointer-events: auto;
    }

    .toast__message {
      flex: 1;
      font-size: var(--text-s);
    }

    .toast__action,
    .toast__close {
      min-height: 36px;
      border: none;
      border-radius: var(--radius-s);
      background: transparent;
      color: inherit;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }

    .toast__action {
      padding: 0 var(--space-3);
      text-decoration: underline;
    }

    .toast__close {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 36px;
    }
  `,
})
export class ToastOutlet {
  protected readonly service = inject(ToastService);
}
