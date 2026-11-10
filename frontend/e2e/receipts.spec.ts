import { expect, test } from '@playwright/test';

import { createCurrentMonth, signUp } from './helpers';

const PDF = Buffer.from('%PDF-1.7\n1 0 obj << >> endobj\n%%EOF\n');

/** Phase 9: receipts on an entry, stored in S3, plus a report exported as CSV. */
test('attach a receipt to an entry, then export the report', async ({ page }) => {
  await signUp(page);
  await createCurrentMonth(page);

  const quick = page.getByRole('form', { name: 'Quick entry' });
  await quick.getByLabel('Amount').fill('42');
  await quick.getByLabel('To').selectOption({ label: 'Food' });
  await quick.getByRole('button', { name: 'Add €42.00' }).click();
  await expect(page.getByText('€42.00 added to Food')).toBeVisible();

  await page.getByRole('button', { name: /^Receipts for Food/ }).click();
  const dialog = page.getByRole('dialog', { name: /Receipts · Food/ });
  await dialog.locator('input[type=file]').setInputFiles([
    { name: 'groceries.pdf', mimeType: 'application/pdf', buffer: PDF },
    { name: 'notes.txt', mimeType: 'text/plain', buffer: Buffer.from('hello') },
  ]);
  await expect(dialog.getByText('groceries.pdf')).toBeVisible();
  await expect(dialog.getByRole('alert')).toContainText('notes.txt');

  // View opens a new tab on the file itself, through a link signed for a few minutes.
  const signed = page.context().waitForEvent('request', (r) => r.url().includes('X-Amz-Signature'));
  const tab = page.waitForEvent('popup');
  await dialog.getByRole('button', { name: 'View groceries.pdf' }).click();
  expect(new URL((await signed).url()).pathname).toMatch(/\/attachments\/[0-9a-f-]{36}$/);
  await (await tab).close();

  await dialog.getByRole('button', { name: 'Close' }).click();
  await expect(page.getByRole('button', { name: 'Receipts for Food (1)' })).toBeVisible();

  // Delete and Undo.
  await page.getByRole('button', { name: 'Receipts for Food (1)' }).click();
  await dialog.getByRole('button', { name: 'Delete groceries.pdf' }).click();
  await expect(dialog.getByText('groceries.pdf deleted')).toBeVisible();
  await dialog.getByRole('button', { name: 'Undo' }).click();
  await expect(dialog.getByRole('button', { name: 'View groceries.pdf' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Close' }).click();

  // The report's entries as CSV.
  await page.getByRole('link', { name: 'Reports' }).click();
  await page.getByRole('button', { name: 'Export' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('menuitem', { name: /CSV/ }).click();
  expect((await download).suggestedFilename()).toMatch(/^finnancial-report-.*\.csv$/);
});
