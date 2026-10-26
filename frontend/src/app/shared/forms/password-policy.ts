import { AbstractControl, ValidationErrors } from '@angular/forms';

/** Same rules as the backend (app/domain/passwords.py). */
export function passwordPolicy(control: AbstractControl<string>): ValidationErrors | null {
  const value = control.value ?? '';
  if (value === '') return null; // `required` reports empty fields
  const ok =
    value.length >= 8 &&
    /\p{Ll}/u.test(value) &&
    /\p{Lu}/u.test(value) &&
    /\p{Nd}/u.test(value) &&
    /[^\p{L}\p{N}\s]/u.test(value);
  return ok ? null : { passwordPolicy: true };
}
