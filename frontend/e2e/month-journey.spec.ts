import { expect, test } from '@playwright/test';

import { currentMonthTitle, monthTotals, PASSWORD, signUp } from './helpers';

/**
 * Phase 4 acceptance criterion and the Phase 6 journey: sign up, create a
 * month, distribute €1000, add €50 from outside and €50 from Savings, close
 * the month, read the report, sign out and back in.
 */
test('a month from sign-up to the report', async ({ page }) => {
  const email = await signUp(page);
  const title = currentMonthTitle();

  // Create the first month.
  await expect(page.getByRole('heading', { name: `No sheet for ${title} yet` })).toBeVisible();
  await page.getByRole('button', { name: `Create ${title}` }).click();
  const create = page.getByRole('dialog');
  await expect(create.getByText('This is your first month')).toBeVisible();
  await create.getByRole('button', { name: `Create ${title}` }).click();
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible();

  // Plan: €1000 of salary, all of it distributed.
  await page.getByRole('button', { name: 'Plan' }).click();
  const plan = page.getByRole('dialog');
  await plan.getByRole('button', { name: 'Add income' }).click();
  await plan.getByLabel('Income name 1').fill('Salary');
  await plan.getByLabel('Salary amount').fill('1000');
  await plan.getByLabel(`Housing amount for ${title}`).fill('600');
  await plan.getByLabel(`Food amount for ${title}`).fill('200');
  await plan.getByLabel(`Savings amount for ${title}`).fill('200');
  await plan.getByRole('button', { name: /^Save \d+ changes$/ }).click();
  await expect(plan).toBeHidden();
  await expect
    .poll(() => monthTotals(page))
    .toMatchObject({
      Income: '€1,000.00',
      Spent: '€800.00',
      Saved: '€200.00',
      Unallocated: '€0.00',
    });

  // €50 from outside the app: the income grows with it.
  const quick = page.getByRole('form', { name: 'Quick entry' });
  await quick.getByLabel('Amount').fill('50');
  await quick.getByLabel('To').selectOption({ label: 'Food' });
  await quick.getByRole('button', { name: 'Add €50.00' }).click();
  await expect(page.getByText('€50.00 added to Food')).toBeVisible();
  await expect
    .poll(() => monthTotals(page))
    .toMatchObject({
      Income: '€1,050.00',
      Spent: '€850.00',
      Unallocated: '€0.00',
    });

  // €50 from Savings: a transfer, the income stays.
  await quick.getByLabel('Amount').fill('50');
  await quick.getByLabel('To').selectOption({ label: 'Food' });
  await quick.getByLabel('From').selectOption({ label: 'Savings' });
  await quick.getByRole('button', { name: 'Move €50.00' }).click();
  await expect(page.getByText('€50.00 moved from Savings to Food')).toBeVisible();
  await expect
    .poll(() => monthTotals(page))
    .toMatchObject({
      Income: '€1,050.00',
      Spent: '€900.00',
      Saved: '€150.00',
      Unallocated: '€0.00',
    });
  await expect(page.getByText('Savings → Food')).toBeVisible();

  // Close the month: no more writes.
  await page.getByRole('button', { name: 'Close month' }).click();
  await expect(page.getByText('Closed', { exact: true })).toBeVisible();
  await expect(page.getByRole('form', { name: 'Quick entry' })).toBeHidden();
  await expect(page.getByRole('button', { name: 'Reopen' })).toBeVisible();

  // The report for this month shows the same money.
  await page.goto('/reports?period=last_month');
  const totals = page.getByRole('region', { name: 'Totals' });
  await expect(totals.locator('.total__value')).toHaveText([
    '€1,050.00',
    '€900.00',
    '€150.00',
    '€0.00',
  ]);
  await page.getByRole('button', { name: 'Table' }).click();
  await expect(page.getByRole('row', { name: /^Food/ })).toContainText('€300.00');
  await expect(page.getByRole('row', { name: /^Savings/ })).toContainText('−€50.00');

  // Sign out and back in.
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/auth\/login/);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible();
  await expect(page.getByText('Closed', { exact: true })).toBeVisible();
});
