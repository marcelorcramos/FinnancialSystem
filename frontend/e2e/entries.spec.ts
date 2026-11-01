import { expect, test } from '@playwright/test';

import { currentMonthTitle, monthTotals, signUp } from './helpers';

test('a deleted entry comes back with Undo', async ({ page }) => {
  await signUp(page);
  const title = currentMonthTitle();
  await page.getByRole('button', { name: `Create ${title}` }).click();
  await page
    .getByRole('dialog')
    .getByRole('button', { name: `Create ${title}` })
    .click();

  const quick = page.getByRole('form', { name: 'Quick entry' });
  await quick.getByLabel('Amount').fill('25');
  await quick.getByLabel('To').selectOption({ label: 'Water' });
  await quick.getByRole('button', { name: 'Add €25.00' }).click();
  await expect.poll(() => monthTotals(page)).toMatchObject({ Income: '€25.00' });

  await page.getByRole('button', { name: 'Delete Water' }).click();
  await expect.poll(() => monthTotals(page)).toMatchObject({ Income: '€0.00' });
  await page.getByRole('button', { name: 'Undo' }).click();
  await expect.poll(() => monthTotals(page)).toMatchObject({ Income: '€25.00' });
});

test('preferences change the whole app and stay', async ({ page }) => {
  await signUp(page);
  await page.goto('/preferences');
  await page.getByRole('button', { name: 'Light', exact: true }).click();
  await page.getByRole('button', { name: 'Larger', exact: true }).click();
  await page.getByRole('switch', { name: 'Reduce motion' }).click();

  const root = page.locator('html');
  await expect(root).toHaveAttribute('data-theme', 'light');
  await expect(root).toHaveAttribute('data-text-size', 'larger');
  await expect(root).toHaveAttribute('data-reduce-motion', '');
  await page.reload();
  await expect(root).toHaveAttribute('data-theme', 'light');
  await expect(page.getByRole('switch', { name: 'Reduce motion' })).toHaveAttribute(
    'aria-checked',
    'true',
  );
});
