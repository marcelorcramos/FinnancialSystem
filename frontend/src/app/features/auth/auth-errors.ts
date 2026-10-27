import { HttpErrorResponse } from '@angular/common/http';

/** User-facing message for an error returned by login or register. */
export function authErrorMessage(error: unknown, context: 'login' | 'register'): string {
  const unknown = 'Something went wrong. Please try again.';
  if (!(error instanceof HttpErrorResponse)) return unknown;
  switch (error.status) {
    case 0:
      return 'Could not reach the server. Please try again.';
    case 401:
      return context === 'login' ? 'Incorrect email or password.' : unknown;
    case 409:
      return 'An account with this email already exists.';
    case 400:
    case 422:
      return 'Please check the data you entered.';
    default:
      return unknown;
  }
}
