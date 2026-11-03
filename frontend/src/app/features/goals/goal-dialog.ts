import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { GoalRead, GoalType, LabelRead } from '../../core/api/types';
import { fromCents, toCents } from '../../shared/money/cents';
import { Icon } from '../../shared/ui/icon';
import { GoalsApi } from './goals-api';

export interface GoalDialogData {
  /** Usable labels without an active goal (plus the edited goal's own label). */
  labels: LabelRead[];
  goal?: GoalRead;
}

/** Creates or edits a goal: a fixed target, or the emergency fund in months of expenses. */
@Component({
  selector: 'app-goal-dialog',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './goal-dialog.html',
  styleUrls: ['../month/add-money-dialog.scss', './goal-dialog.scss'],
})
export class GoalDialog {
  private readonly api = inject(GoalsApi);
  protected readonly ref = inject<DialogRef<GoalRead>>(DialogRef);
  protected readonly data = inject<GoalDialogData>(DIALOG_DATA);
  protected readonly editing = !!this.data.goal;

  private readonly emergencyLabel = this.data.labels.find((l) => l.name === 'Emergency Fund');
  protected readonly type = signal<GoalType>(this.data.goal?.type ?? 'normal');
  protected readonly labelId = signal(this.data.goal?.label_id ?? this.data.labels[0]?.id ?? '');
  protected readonly targetText = signal(
    this.data.goal?.type === 'normal' ? (this.data.goal.target_amount ?? '') : '',
  );
  protected readonly monthsText = signal(String(this.data.goal?.months_of_expenses ?? 6));
  protected readonly deadline = signal(this.data.goal?.deadline ?? '');
  protected readonly manual = signal(this.data.goal?.manual_progress != null);
  protected readonly manualText = signal(this.data.goal?.manual_progress ?? '');
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  private readonly targetCents = computed(() => toCents(this.targetText()));
  private readonly months = computed(() => {
    const value = Number(this.monthsText());
    return Number.isInteger(value) && value >= 1 && value <= 24 ? value : null;
  });
  private readonly manualCents = computed(() => toCents(this.manualText()));
  protected readonly valid = computed(
    () =>
      !!this.labelId() &&
      (this.type() === 'normal' ? (this.targetCents() ?? 0) > 0 : this.months() !== null) &&
      (!this.manual() || this.manualCents() !== null),
  );

  protected setType(type: GoalType): void {
    this.type.set(type);
    // The emergency fund usually lives in the Emergency Fund label.
    if (type === 'emergency_fund' && !this.editing && this.emergencyLabel) {
      this.labelId.set(this.emergencyLabel.id);
    }
  }

  protected save(): void {
    if (!this.valid() || this.pending()) return;
    const normal = this.type() === 'normal';
    const target = normal ? fromCents(this.targetCents()!) : null;
    const months = normal ? null : this.months();
    const manual = this.manual() ? fromCents(this.manualCents()!) : null;
    const deadline = this.deadline() || null;
    const request: Observable<GoalRead> = this.data.goal
      ? this.api.update(this.data.goal.id, {
          ...(normal ? { target_amount: target } : { months_of_expenses: months }),
          deadline,
          manual_progress: manual,
        })
      : this.api.create({
          label_id: this.labelId(),
          type: this.type(),
          target_amount: target,
          months_of_expenses: months,
          deadline,
          manual_progress: manual,
        });
    this.pending.set(true);
    this.error.set(null);
    request.subscribe({
      next: (goal) => this.ref.close(goal),
      error: (error: unknown) => {
        this.pending.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
