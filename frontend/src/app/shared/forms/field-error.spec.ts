import { FormControl, Validators } from '@angular/forms';

import { fieldError } from './field-error';

describe('fieldError', () => {
  it('returns null for a valid control', () => {
    expect(fieldError(new FormControl('x', Validators.required))).toBeNull();
  });

  it('maps validator errors to translation keys with params', () => {
    expect(fieldError(new FormControl('', Validators.required))).toEqual({
      key: 'validation.required',
    });
    expect(fieldError(new FormControl('abc', Validators.minLength(8)))).toEqual({
      key: 'validation.minLength',
      params: { min: 8 },
    });
    expect(fieldError(new FormControl('a@', Validators.email))).toEqual({
      key: 'validation.email',
    });
  });
});
