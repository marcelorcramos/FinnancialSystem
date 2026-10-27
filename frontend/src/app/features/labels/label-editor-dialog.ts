import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';

import { apiErrorMessage } from '../../core/api/api-errors';
import { LabelKind, LabelRead } from '../../core/api/types';
import { visibleError } from '../../shared/forms/field-error';
import { KIND_NAMES, KINDS } from '../../shared/money/kind';
import { Icon, isIconName, LABEL_ICONS } from '../../shared/ui/icon';
import { LabelsApi } from './labels-api';

export interface LabelEditorData {
  /** The label to edit; absent to create a new one. */
  label?: LabelRead;
}

const HEX_COLOR = /^#[0-9A-Fa-f]{6}$/;

const KIND_HELP: Record<LabelKind, string> = {
  expense: 'Money you spend: rent, food, bills.',
  saving: 'Money you put aside to use later.',
  investment: 'Money you invest to grow: ETFs, funds.',
};

/** Create or edit a label: name, kind, one of 8 free colors or any #hex, and an icon. */
@Component({
  selector: 'app-label-editor-dialog',
  imports: [Icon, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './label-editor-dialog.html',
  styleUrl: './label-editor-dialog.scss',
})
export class LabelEditorDialog implements OnInit {
  private readonly api = inject(LabelsApi);
  protected readonly ref = inject<DialogRef<LabelRead>>(DialogRef);
  protected readonly data = inject<LabelEditorData>(DIALOG_DATA, { optional: true }) ?? {};

  protected readonly editing = !!this.data.label;
  protected readonly kinds = KINDS.map((kind) => ({
    kind,
    name: KIND_NAMES[kind],
    help: KIND_HELP[kind],
  }));
  protected readonly icons = LABEL_ICONS;
  protected readonly swatches = signal<string[]>([]);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly visibleError = visibleError;

  protected readonly form = inject(NonNullableFormBuilder).group({
    name: [this.data.label?.name ?? '', [Validators.required, Validators.maxLength(50)]],
    kind: [this.data.label?.kind ?? ('expense' as LabelKind), Validators.required],
    color: [this.data.label?.color ?? '', [Validators.required, Validators.pattern(HEX_COLOR)]],
    icon: [
      this.data.label && isIconName(this.data.label.icon) ? this.data.label.icon : 'restaurant',
      Validators.required,
    ],
  });

  private readonly value = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });
  protected readonly preview = computed(() => {
    const value = { ...this.form.getRawValue(), ...this.value() };
    return {
      name: value.name?.trim() || 'Untitled label',
      color: HEX_COLOR.test(value.color ?? '') ? value.color : 'transparent',
      icon: value.icon && isIconName(value.icon) ? value.icon : 'labels',
      kind: KIND_NAMES[(value.kind ?? 'expense') as LabelKind],
    };
  });
  protected readonly kindChanged = computed(
    () =>
      this.editing &&
      this.value().kind !== undefined &&
      this.value().kind !== this.data.label?.kind,
  );

  ngOnInit(): void {
    this.api.colorSuggestions().subscribe((colors) => {
      const current = this.data.label?.color;
      this.swatches.set(current ? [current, ...colors.slice(0, 7)] : colors);
      if (!this.form.controls.color.value && colors[0]) {
        this.form.controls.color.setValue(colors[0]);
      }
    });
  }

  protected save(): void {
    if (this.pending()) return;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { name, kind, color, icon } = this.form.getRawValue();
    const body = { name: name.trim(), kind, color: color.toUpperCase(), icon };
    const request: Observable<LabelRead> = this.data.label
      ? this.api.update(this.data.label.id, body)
      : this.api.create(body);
    this.pending.set(true);
    this.error.set(null);
    request.subscribe({
      next: (label) => this.ref.close(label),
      error: (error: unknown) => {
        this.pending.set(false);
        this.error.set(apiErrorMessage(error));
      },
    });
  }
}
