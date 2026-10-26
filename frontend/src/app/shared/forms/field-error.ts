import { AbstractControl } from '@angular/forms';

export interface FieldError {
  key: string;
  params?: Record<string, unknown>;
}

/** Translation key (and params) for the first error of a control. */
export function fieldError(control: AbstractControl): FieldError | null {
  const errors = control.errors;
  if (!errors) return null;
  if (errors['required']) return { key: 'validation.required' };
  if (errors['email']) return { key: 'validation.email' };
  if (errors['minlength']) {
    return { key: 'validation.minLength', params: { min: errors['minlength'].requiredLength } };
  }
  if (errors['maxlength']) {
    return { key: 'validation.maxLength', params: { max: errors['maxlength'].requiredLength } };
  }
  if (errors['passwordPolicy']) return { key: 'validation.passwordPolicy' };
  if (errors['passwordMismatch']) return { key: 'validation.passwordMismatch' };
  return null;
}
