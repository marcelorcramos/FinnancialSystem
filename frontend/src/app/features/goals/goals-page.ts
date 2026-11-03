import { Dialog } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { GoalList, GoalRead, LabelRead } from '../../core/api/types';
import { dialogA11y } from '../../shared/ui/dialog-a11y';
import { Icon, IconName, isIconName } from '../../shared/ui/icon';
import { ToastService } from '../../shared/ui/toast.service';
import { LabelsApi } from '../labels/labels-api';
import { GoalDialog, GoalDialogData } from './goal-dialog';
import { completedText, goalCard } from './goal-view';
import { GoalsApi } from './goals-api';

type LoadState = 'loading' | 'ready' | 'error';

/** Active goals with their pace, the emergency fund, and the completed ones. */
@Component({
  selector: 'app-goals-page',
  imports: [Icon],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './goals-page.html',
  styleUrl: './goals-page.scss',
})
export default class GoalsPage {
  private readonly api = inject(GoalsApi);
  private readonly labelsApi = inject(LabelsApi);
  private readonly dialog = inject(Dialog);
  private readonly toasts = inject(ToastService);

  protected readonly state = signal<LoadState>('loading');
  private readonly goals = signal<GoalList>({ active: [], completed: [] });
  private readonly labels = signal<LabelRead[]>([]);

  protected readonly active = computed(() =>
    this.goals().active.map((goal) => ({ goal, card: goalCard(goal) })),
  );
  protected readonly completed = computed(() =>
    this.goals().completed.map((goal) => ({
      goal,
      card: goalCard(goal),
      when: completedText(goal),
    })),
  );
  /** Labels that can take a new goal: usable and without an active one. */
  private readonly freeLabels = computed(() => {
    const taken = new Set(this.goals().active.map((g) => g.label_id));
    return this.labels().filter((l) => !l.archived_at && !taken.has(l.id));
  });

  constructor() {
    this.load();
  }

  protected iconOf(icon: string): IconName {
    return isIconName(icon) ? icon : 'target';
  }

  protected load(): void {
    forkJoin([this.api.list(), this.labelsApi.list()]).subscribe({
      next: ([goals, labels]) => {
        this.goals.set(goals);
        this.labels.set(labels);
        this.state.set('ready');
      },
      error: () => this.state.set('error'),
    });
  }

  protected create(): void {
    this.open({ labels: this.freeLabels() }, 'Goal created');
  }

  protected edit(goal: GoalRead): void {
    const own = this.labels().filter((l) => l.id === goal.label_id);
    this.open({ labels: own, goal }, 'Goal saved');
  }

  protected remove(goal: GoalRead): void {
    this.api.delete(goal.id).subscribe({
      next: () => {
        this.toasts.show(`Goal for ${goal.label_name} deleted`, {
          label: 'Undo',
          run: () =>
            this.api.restore(goal.id).subscribe({
              next: () => this.load(),
              error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
            }),
        });
        this.load();
      },
      error: (error: unknown) => this.toasts.show(apiErrorMessage(error)),
    });
  }

  private open(data: GoalDialogData, message: string): void {
    this.dialog
      .open<GoalRead, GoalDialogData>(GoalDialog, { data, ...dialogA11y('goal-title') })
      .closed.subscribe((goal) => {
        if (!goal) return;
        this.toasts.show(message);
        this.load();
      });
  }
}
