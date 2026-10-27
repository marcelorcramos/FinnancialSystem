import { AbstractControl } from '@angular/forms';

/** Message for the first validation error of a control, or null when it is valid. */
export function fieldError(control: AbstractControl): string | null {
  const errors = control.errors;
  if (!errors) return null;
  if (errors['required']) return 'This field is required.';
  if (errors['email']) return 'Enter a valid email.';
  if (errors['minlength']) return `At least ${errors['minlength'].requiredLength} characters.`;
  if (errors['maxlength']) return `At most ${errors['maxlength'].requiredLength} characters.`;
  if (errors['passwordPolicy']) {
    return 'Use at least 8 characters with an uppercase, a lowercase, a number and a symbol.';
  }
  if (errors['passwordMismatch']) return 'Passwords do not match.';
  return null;
}

/** The error to show next to a field: only once the user has touched it. */
export function visibleError(control: AbstractControl): string | null {
  return control.touched ? fieldError(control) : null;
}
