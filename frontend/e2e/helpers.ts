import { expect, Page } from '@playwright/test';

export const PASSWORD = 'E2e-password-1!';

/** A new account per test, so tests never share data. */
export async function signUp(page: Page, name = 'E2E User'): Promise<string> {
  const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
  await page.goto('/auth/register');
  await page.getByLabel('Name').fill(name);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByLabel('Confirm password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page).toHaveURL(/\/month\/\d{4}\/\d{1,2}$/);
  return email;
}

/** "November 2026" for the current month, as the app titles it. */
export function currentMonthTitle(now = new Date()): string {
  return now.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

/** Totals on the month screen, by their label (Income, Spent, …). */
export async function monthTotals(page: Page): Promise<Record<string, string>> {
  const cards = page.getByRole('region', { name: 'Totals' }).locator('.total');
  const entries = await cards.evaluateAll((nodes) =>
    nodes.map((node) => [
      node.querySelector('.total__label')?.textContent?.trim() ?? '',
      node.querySelector('.total__value')?.textContent?.trim() ?? '',
    ]),
  );
  return Object.fromEntries(entries);
}
