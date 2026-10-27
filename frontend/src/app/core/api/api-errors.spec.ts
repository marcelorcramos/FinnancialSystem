import { HttpErrorResponse } from '@angular/common/http';

import { apiErrorMessage } from './api-errors';

describe('apiErrorMessage', () => {
  it('uses the detail sent by the API', () => {
    const error = new HttpErrorResponse({ status: 409, error: { detail: 'Already exists' } });
    expect(apiErrorMessage(error)).toBe('Already exists');
  });

  it('falls back to a generic message', () => {
    expect(apiErrorMessage(new HttpErrorResponse({ status: 422, error: { detail: [] } }))).toBe(
      'Something went wrong. Please try again.',
    );
    expect(apiErrorMessage(new Error('boom'))).toBe('Something went wrong. Please try again.');
  });
});
