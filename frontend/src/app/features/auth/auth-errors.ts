import { HttpErrorResponse } from '@angular/common/http';

/** Translation key for an error returned by login or register. */
export function authErrorKey(error: unknown, context: 'login' | 'register'): string {
  if (!(error instanceof HttpErrorResponse)) return 'auth.errors.unknown';
  switch (error.status) {
    case 0:
      return 'auth.errors.network';
    case 401:
      return context === 'login' ? 'auth.errors.invalidCredentials' : 'auth.errors.unknown';
    case 409:
      return 'auth.errors.emailTaken';
    case 400:
    case 422:
      return 'auth.errors.invalidData';
    default:
      return 'auth.errors.unknown';
  }
}
