import { expect, test } from '@playwright/test';

import { emailedLink, PASSWORD, signUp } from './helpers';

const NEW_PASSWORD = 'E2e-new-password-2!';

/** Phase 9: email confirmation and password recovery through Mailpit. */
test('confirm the email, then recover a forgotten password', async ({ page }) => {
  const email = await signUp(page);
  const reminder = page.getByRole('region', { name: 'Confirm your email' });
  await expect(reminder).toContainText(email);

  // The link from the sign-up email confirms the address.
  await page.goto(await emailedLink(page, email, 'Confirm your email'));
  await expect(page.getByText('Your email is confirmed')).toBeVisible();
  await page.getByRole('link', { name: 'Continue' }).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(reminder).toBeHidden();

  // Signed out, ask for a reset link.
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await page.getByRole('link', { name: 'Forgot your password?' }).click();
  await expect(page).toHaveURL(/\/auth\/forgot-password$/);
  await page.getByLabel('Email').fill(email);
  await page.getByRole('button', { name: 'Send reset link' }).click();
  await expect(page.getByText(`If ${email} has an account`)).toBeVisible();

  // Choose a new password from the emailed link, then sign in with it.
  await page.goto(await emailedLink(page, email, 'Reset your password'));
  await page.getByLabel('New password').fill(NEW_PASSWORD);
  await page.getByRole('button', { name: 'Save new password' }).click();
  await expect(page.getByText('Password changed. Sign in with the new one.')).toBeVisible();
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Incorrect email or password.')).toBeVisible();
  await page.getByLabel('Password', { exact: true }).fill(NEW_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/month\/\d{4}\/\d{1,2}$/);
});

/** Phase 9: the GDPR data export and deleting the account for good. */
test('download my data, then delete the account', async ({ page }) => {
  const email = await signUp(page);
  await page.goto('/account');

  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download my data' }).click();
  expect((await download).suggestedFilename()).toMatch(/^finnancial-data-\d{4}-\d{2}-\d{2}\.zip$/);

  await page.getByRole('button', { name: 'Delete account' }).click();
  const dialog = page.getByRole('alertdialog', { name: 'Delete your account?' });
  await dialog.getByLabel('Password').fill(PASSWORD);
  await dialog.getByLabel('I understand this cannot be undone').check();
  await dialog.getByRole('button', { name: 'Delete account' }).click();
  await expect(page).toHaveURL(/\/auth\/login/);
  await expect(page.getByText('Your account was deleted')).toBeVisible();

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByText('Incorrect email or password.')).toBeVisible();
});
