import { FormControl, Validators } from '@angular/forms';

import { fieldError, visibleError } from './field-error';

describe('fieldError', () => {
  it('returns null for a valid control', () => {
    expect(fieldError(new FormControl('x', Validators.required))).toBeNull();
  });

  it('maps validator errors to messages', () => {
    expect(fieldError(new FormControl('', Validators.required))).toBe('This field is required.');
    expect(fieldError(new FormControl('abc', Validators.minLength(8)))).toBe(
      'At least 8 characters.',
    );
    expect(fieldError(new FormControl('a@', Validators.email))).toBe('Enter a valid email.');
  });
});

describe('visibleError', () => {
  it('waits until the control was touched', () => {
    const control = new FormControl('', Validators.required);
    expect(visibleError(control)).toBeNull();

    control.markAsTouched();
    expect(visibleError(control)).toBe('This field is required.');
  });
});
