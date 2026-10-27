import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { LabelRead } from '../../core/api/types';

export interface DeleteLabelData {
  label: LabelRead;
  /** Labels that can receive the entries (active, not archived, not this one). */
  targets: LabelRead[];
}

export type DeleteLabelChoice = { action: 'reassign'; targetId: string } | { action: 'archive' };

/** Asked when a label with entries is deleted: move its entries, or archive it instead. */
@Component({
  selector: 'app-delete-label-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section
      class="dialog"
      role="alertdialog"
      aria-labelledby="delete-title"
      aria-describedby="delete-text"
    >
      <h2 id="delete-title">Delete “{{ data.label.name }}”?</h2>
      <p id="delete-text">
        This label has entries. Money never disappears, so its entries move to another label first.
      </p>
      <div class="field">
        <label for="delete-target">Move entries to</label>
        <select
          id="delete-target"
          class="field__input"
          [value]="targetId()"
          (change)="targetId.set($any($event.target).value)"
        >
          @for (target of data.targets; track target.id) {
            <option [value]="target.id">{{ target.name }}</option>
          }
        </select>
      </div>
      <p class="hint">
        Prefer to keep its history? Archive it instead: it stops receiving money but stays in past
        reports.
      </p>
      <div class="actions">
        <button type="button" class="btn" (click)="ref.close()">Cancel</button>
        <button type="button" class="btn" (click)="ref.close({ action: 'archive' })">
          Archive instead
        </button>
        <button
          type="button"
          class="btn btn--danger"
          [disabled]="!targetId()"
          (click)="ref.close({ action: 'reassign', targetId: targetId() })"
        >
          Move and delete
        </button>
      </div>
    </section>
  `,
  styles: `
    .dialog {
      display: flex;
      flex-direction: column;
      gap: var(--space-4);
      width: min(480px, calc(100vw - 32px));
      padding: var(--space-5);
      border: 1px solid var(--color-danger);
      border-radius: var(--radius-m);
      background: var(--color-surface);
      color: var(--color-text);
    }

    h2 {
      font-size: var(--text-l);
    }

    p {
      margin: 0;
      color: var(--color-text-muted);
    }

    .hint {
      font-size: var(--text-s);
      color: var(--color-text-subtle);
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: var(--space-2);
    }
  `,
})
export class DeleteLabelDialog {
  protected readonly data = inject<DeleteLabelData>(DIALOG_DATA);
  protected readonly ref = inject<DialogRef<DeleteLabelChoice>>(DialogRef);
  protected readonly targetId = signal(this.data.targets[0]?.id ?? '');
}
