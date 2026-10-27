import { Dialog } from '@angular/cdk/dialog';
import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { LabelRead } from '../../core/api/types';
import { KIND_NAMES, KINDS } from '../../shared/money/kind';
import { Icon } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { DeleteLabelChoice, DeleteLabelData, DeleteLabelDialog } from './delete-label-dialog';
import { LabelsApi } from './labels-api';

@Component({
  selector: 'app-labels-page',
  imports: [CdkMenu, CdkMenuItem, CdkMenuTrigger, Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './labels-page.html',
  styleUrl: './labels-page.scss',
})
export default class LabelsPage implements OnInit {
  private readonly api = inject(LabelsApi);
  private readonly dialog = inject(Dialog);
  private readonly toasts = inject(ToastService);

  protected readonly labels = signal<LabelRead[]>([]);
  protected readonly loading = signal(true);
  protected readonly loadError = signal(false);

  protected readonly active = computed(() => this.labels().filter((l) => !l.archived_at));
  protected readonly archived = computed(() => this.labels().filter((l) => l.archived_at));
  protected readonly groups = computed(() =>
    KINDS.map((kind) => ({
      kind,
      title: KIND_NAMES[kind],
      labels: this.active().filter((label) => label.kind === kind),
    })),
  );

  ngOnInit(): void {
    this.reload();
  }

  protected reload(): void {
    this.api.list(true).subscribe({
      next: (labels) => {
        this.labels.set(labels);
        this.loading.set(false);
        this.loadError.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.loadError.set(true);
      },
    });
  }

  protected archive(label: LabelRead): void {
    this.run(this.api.archive(label.id), `“${label.name}” archived`, {
      label: 'Undo',
      run: () => this.run(this.api.unarchive(label.id)),
    });
  }

  protected unarchive(label: LabelRead): void {
    this.run(this.api.unarchive(label.id), `“${label.name}” is back`);
  }

  protected delete(label: LabelRead): void {
    this.api.delete(label.id).subscribe({
      next: () => this.afterDelete(label),
      error: (error: unknown) => {
        if (error instanceof HttpErrorResponse && error.status === 409) {
          this.askHowToDelete(label);
        } else {
          this.toasts.show(apiErrorMessage(error));
        }
      },
    });
  }

  private askHowToDelete(label: LabelRead): void {
    const data: DeleteLabelData = {
      label,
      targets: this.active().filter((l) => l.id !== label.id),
    };
    this.dialog
      .open<DeleteLabelChoice, DeleteLabelData>(DeleteLabelDialog, { data })
      .closed.subscribe((choice) => {
        if (choice?.action === 'archive') {
          this.archive(label);
        } else if (choice?.action === 'reassign') {
          this.api.delete(label.id, choice.targetId).subscribe({
            next: () => this.afterDelete(label),
            error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
          });
        }
      });
  }

  private afterDelete(label: LabelRead): void {
    this.reload();
    this.toasts.show(`“${label.name}” deleted`, {
      label: 'Undo',
      run: () => this.run(this.api.restore(label.id)),
    });
  }

  private run(
    request: Observable<unknown>,
    message?: string,
    action?: { label: string; run: () => void },
  ): void {
    request.subscribe({
      next: () => {
        this.reload();
        if (message) this.toasts.show(message, action);
      },
      error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
    });
  }
}
