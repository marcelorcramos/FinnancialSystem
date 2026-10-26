import { HttpErrorResponse } from '@angular/common/http';

import { authErrorKey } from './auth-errors';

const http = (status: number) => new HttpErrorResponse({ status });

describe('authErrorKey', () => {
  it.each([
    [http(0), 'login', 'auth.errors.network'],
    [http(401), 'login', 'auth.errors.invalidCredentials'],
    [http(409), 'register', 'auth.errors.emailTaken'],
    [http(422), 'register', 'auth.errors.invalidData'],
    [http(500), 'login', 'auth.errors.unknown'],
    [new Error('boom'), 'login', 'auth.errors.unknown'],
  ] as const)('maps %s on %s to %s', (error, context, key) => {
    expect(authErrorKey(error, context)).toBe(key);
  });
});
