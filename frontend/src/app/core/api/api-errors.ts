import { HttpErrorResponse } from '@angular/common/http';

/** The `detail` message of an API error, or a generic message. */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') {
    return error.error.detail;
  }
  return 'Something went wrong. Please try again.';
}
