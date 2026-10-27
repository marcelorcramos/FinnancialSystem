import { HttpErrorResponse } from '@angular/common/http';

import { authErrorMessage } from './auth-errors';

const http = (status: number) => new HttpErrorResponse({ status });

describe('authErrorMessage', () => {
  it.each([
    [http(0), 'login', 'Could not reach the server. Please try again.'],
    [http(401), 'login', 'Incorrect email or password.'],
    [http(409), 'register', 'An account with this email already exists.'],
    [http(422), 'register', 'Please check the data you entered.'],
    [http(500), 'login', 'Something went wrong. Please try again.'],
    [new Error('boom'), 'login', 'Something went wrong. Please try again.'],
  ] as const)('maps %s on %s to "%s"', (error, context, message) => {
    expect(authErrorMessage(error, context)).toBe(message);
  });
});
