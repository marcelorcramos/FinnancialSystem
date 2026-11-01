import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests against a running stack. Locally: start it with
 * `docker compose -f deploy/docker-compose.yml up -d --build` and run
 * `npx playwright test` (the web container serves the app on :8080).
 * E2E_BASE_URL points the tests elsewhere, e.g. the dev server on :4200.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env['CI'],
  retries: process.env['CI'] ? 1 : 0,
  reporter: process.env['CI'] ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env['E2E_BASE_URL'] ?? 'http://localhost:8080',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'phone', use: { ...devices['Pixel 7'] } },
  ],
});
