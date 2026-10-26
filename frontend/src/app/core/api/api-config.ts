import { InjectionToken } from '@angular/core';

/**
 * Base URL of the backend API. Relative by default: the dev server proxies
 * /api to http://localhost:8000 (proxy.conf.json) and nginx does the same in
 * the container, so the refresh cookie stays first-party.
 */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: () => '/api/v1',
});
