import { AbstractControl, ValidationErrors } from '@angular/forms';

export interface PasswordRule {
  label: string;
  met: boolean;
}

/** Each rule of the password policy, for a live checklist. Same rules as the backend. */
export function passwordRules(value: string): PasswordRule[] {
  return [
    { label: 'At least 8 characters', met: value.length >= 8 },
    { label: 'A lowercase letter', met: /\p{Ll}/u.test(value) },
    { label: 'An uppercase letter', met: /\p{Lu}/u.test(value) },
    { label: 'A number', met: /\p{Nd}/u.test(value) },
    { label: 'A special character', met: /[^\p{L}\p{N}\s]/u.test(value) },
  ];
}

/** Same rules as the backend (app/domain/passwords.py). */
export function passwordPolicy(control: AbstractControl<string>): ValidationErrors | null {
  const value = control.value ?? '';
  if (value === '') return null; // `required` reports empty fields
  return passwordRules(value).every((rule) => rule.met) ? null : { passwordPolicy: true };
}
