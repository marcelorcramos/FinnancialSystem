import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { concatMap, finalize, from } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { AttachmentRead } from '../../core/api/types';
import { download, fileSize, openInNewTab } from '../../shared/files/open-file';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { RECEIPT_TYPES, ReceiptsApi, receiptProblem } from './receipts-api';

export interface ReceiptsDialogData {
  monthId: string;
  monthTitle: string;
  /** Only this entry's receipts, and new ones are tied to it. Null: the whole month. */
  entry: { id: string; title: string } | null;
  closed: boolean;
  /** Entry titles by id, to say which entry a receipt belongs to. */
  entryTitles: Record<string, string>;
}

/** Receipts of a month or of one entry: add, view, download and delete with Undo. */
@Component({
  selector: 'app-receipts-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="dialog">
      <header class="head">
        <h2 id="receipts-title">Receipts · {{ data.entry?.title ?? data.monthTitle }}</h2>
        <button
          type="button"
          class="btn btn--icon btn--quiet"
          aria-label="Close"
          (click)="ref.close()"
        >
          <app-icon name="close" />
        </button>
      </header>

      @if (error(); as message) {
        <div class="alert" role="alert">
          <app-icon name="alert" [size]="18" />
          <span>{{ message }}</span>
        </div>
      }

      @if (loading()) {
        <p class="muted" role="status">Loading…</p>
      } @else {
        <ul class="files" aria-label="Receipts">
          @for (receipt of shown(); track receipt.id) {
            <li class="file">
              <app-icon [name]="receipt.mime === 'application/pdf' ? 'file' : 'paperclip'" />
              <span class="file__text">
                <span class="file__name">{{ receipt.filename }}</span>
                <span class="muted file__meta">
                  {{ size(receipt.size) }}
                  @if (!data.entry && receipt.entry_id) {
                    · {{ data.entryTitles[receipt.entry_id] ?? 'Entry' }}
                  }
                </span>
              </span>
              <button
                type="button"
                class="btn btn--icon btn--quiet"
                [attr.aria-label]="'View ' + receipt.filename"
                (click)="view(receipt)"
              >
                <app-icon name="eye" [size]="18" />
              </button>
              <button
                type="button"
                class="btn btn--icon btn--quiet"
                [attr.aria-label]="'Download ' + receipt.filename"
                (click)="save(receipt)"
              >
                <app-icon name="download" [size]="18" />
              </button>
              @if (!data.closed) {
                <button
                  type="button"
                  class="btn btn--icon btn--quiet"
                  [attr.aria-label]="'Delete ' + receipt.filename"
                  (click)="remove(receipt)"
                >
                  <app-icon name="trash" [size]="18" />
                </button>
              }
            </li>
          } @empty {
            @if (!deleted().length) {
              <li class="muted empty">No receipts yet.</li>
            }
          }
          <!-- Undo lives here: a toast would sit behind the dialog. -->
          @for (receipt of deleted(); track receipt.id) {
            <li class="file file--deleted" role="status">
              <app-icon name="trash" [size]="18" />
              <span class="file__text muted">{{ receipt.filename }} deleted</span>
              <button type="button" class="btn btn--quiet" (click)="undo(receipt)">Undo</button>
            </li>
          }
        </ul>

        @if (data.closed) {
          <p class="muted">The month is closed: reopen it to add or delete receipts.</p>
        } @else {
          <label class="btn btn--primary upload" [class.upload--busy]="uploading()">
            <input
              class="visually-hidden"
              type="file"
              multiple
              [accept]="accept"
              [disabled]="uploading()"
              (change)="pick($event)"
            />
            @if (uploading()) {
              <span class="spinner" aria-hidden="true"></span> Uploading…
            } @else {
              <app-icon name="plus" [size]="18" /> Add receipts
            }
          </label>
          <p class="muted hint">JPEG, PNG, WebP or PDF, up to 10 MB each.</p>
        }
      }
    </section>
  `,
  styleUrl: './add-money-dialog.scss',
  styles: `
    .files {
      display: flex;
      flex-direction: column;
      gap: var(--space-2);
      margin: 0;
      padding: 0;
      list-style: none;
    }

    .file {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-2) var(--space-3);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-m);
    }

    .file--deleted {
      border-style: dashed;
    }

    .file__text {
      display: flex;
      flex: 1;
      flex-direction: column;
      min-width: 0;
    }

    .file__name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file__meta,
    .hint {
      font-size: var(--text-xs);
    }

    .hint {
      margin: calc(var(--space-2) * -1) 0 0;
    }

    .upload {
      align-self: flex-start;
      cursor: pointer;

      &:focus-within {
        outline: 2px solid var(--color-focus);
        outline-offset: 2px;
      }

      &--busy {
        cursor: progress;
      }
    }
  `,
})
export class ReceiptsDialog {
  private readonly api = inject(ReceiptsApi);
  private readonly toasts = inject(ToastService);
  protected readonly ref = inject<DialogRef<void>>(DialogRef);
  protected readonly data = inject<ReceiptsDialogData>(DIALOG_DATA);

  protected readonly accept = RECEIPT_TYPES.join(',');
  protected readonly receipts = signal<AttachmentRead[]>([]);
  protected readonly loading = signal(true);
  protected readonly uploading = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Deleted while the dialog is open, so they can be brought back. */
  protected readonly deleted = signal<AttachmentRead[]>([]);
  protected readonly shown = computed(() => {
    const entry = this.data.entry;
    return entry ? this.receipts().filter((r) => r.entry_id === entry.id) : this.receipts();
  });
  protected readonly size = fileSize;

  constructor() {
    this.refresh();
  }

  private refresh(): void {
    this.api.list(this.data.monthId).subscribe({
      next: (receipts) => {
        this.receipts.set(receipts);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.error.set(apiErrorMessage(error));
        this.loading.set(false);
      },
    });
  }

  protected pick(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = [...(input.files ?? [])];
    input.value = '';
    const problems = files.map(receiptProblem).filter((p): p is string => p !== null);
    const valid = files.filter((file) => receiptProblem(file) === null);
    this.error.set(problems.length ? problems.join('. ') + '.' : null);
    if (!valid.length) return;

    this.uploading.set(true);
    from(valid)
      .pipe(
        concatMap((file) => this.api.upload(this.data.monthId, file, this.data.entry?.id ?? null)),
        finalize(() => {
          this.uploading.set(false);
          this.refresh();
        }),
      )
      .subscribe({
        next: (receipt) => this.receipts.update((list) => [...list, receipt]),
        error: (error: unknown) => this.error.set(apiErrorMessage(error)),
        complete: () =>
          this.toasts.show(valid.length === 1 ? 'Receipt added' : `${valid.length} receipts added`),
      });
  }

  protected view(receipt: AttachmentRead): void {
    openInNewTab(this.api.url(receipt.id), (error) => this.error.set(apiErrorMessage(error)));
  }

  protected save(receipt: AttachmentRead): void {
    download(this.api.url(receipt.id, true), (error) => this.error.set(apiErrorMessage(error)));
  }

  protected remove(receipt: AttachmentRead): void {
    this.api.remove(receipt.id).subscribe({
      next: () => {
        this.receipts.update((list) => list.filter((r) => r.id !== receipt.id));
        this.deleted.update((list) => [...list, receipt]);
      },
      error: (error: unknown) => this.error.set(apiErrorMessage(error)),
    });
  }

  protected undo(receipt: AttachmentRead): void {
    this.api.restore(receipt.id).subscribe({
      next: () => {
        this.deleted.update((list) => list.filter((r) => r.id !== receipt.id));
        this.refresh();
      },
      error: (error: unknown) => this.error.set(apiErrorMessage(error)),
    });
  }
}
