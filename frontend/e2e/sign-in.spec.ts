import { expect, test } from '@playwright/test';

import { PASSWORD, signUp, totp } from './helpers';

const SHOTS = process.env['E2E_SHOTS'];

/** Phase 10: turn on two-factor sign-in, sign in with a code, then with a recovery code. */
test('two-factor sign-in with an authenticator app', async ({ page }) => {
  const email = await signUp(page);
  await page.goto('/account');

  // Turn it on: read the key under "Can't scan it?" as an authenticator would.
  await page.getByRole('button', { name: 'Turn on' }).click();
  const dialog = page.getByRole('dialog', { name: 'Turn on two-factor sign-in' });
  await expect(dialog.getByRole('img', { name: /QR code/ })).toBeVisible();
  await dialog.getByText("Can't scan it?").click();
  const secret = (await dialog.locator('code').textContent())!.trim();
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/2fa-setup.png` });
  await dialog.getByLabel('Code').fill(totp(secret));
  await dialog.getByRole('button', { name: 'Turn on' }).click();
  const codes = dialog.getByRole('list', { name: 'Recovery codes' }).getByRole('listitem');
  await expect(codes).toHaveCount(10);
  const recovery = (await codes.first().textContent())!.trim();
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/2fa-codes.png` });
  await dialog.getByRole('button', { name: 'I saved them' }).click();
  await expect(page.getByText('Two-factor sign-in is on')).toBeVisible();
  await expect(page.locator('#two-factor')).toContainText('10 recovery codes left');

  // Sign out and back in: the password is not enough any more.
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/auth\/login$/);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/auth\/two-factor$/);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/2fa-login.png` });
  // A code of the next step, so it was not used to turn 2FA on.
  await page.getByLabel('Code').fill(totp(secret, 1));
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page).toHaveURL(/\/month\/\d{4}\/\d{1,2}$/);

  // Lost phone: a recovery code works once.
  await page.getByRole('button', { name: 'Account menu' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/auth\/login$/);
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Lost your phone? Use a recovery code' }).click();
  await page.getByLabel('Recovery code').fill(recovery);
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page).toHaveURL(/\/month\/\d{4}\/\d{1,2}$/);
});

/** Phase 10: "Try it" opens a demo account of its own, full of sample data. */
test('try the demo without signing up', async ({ page }) => {
  await page.goto('/auth/login');
  await page.getByRole('button', { name: 'Try it with sample data' }).click();
  // Six months are written through the normal services: give it time under a busy stack.
  await expect(page.getByRole('region', { name: 'Demo account' })).toContainText(
    'You are exploring a demo',
    { timeout: 20_000 },
  );
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  // Six months of data: the totals are filled and the previous month is closed.
  await expect(page.getByRole('region', { name: 'Totals' })).toContainText('€2,400.00');
  await page.getByRole('link', { name: /^Previous month/ }).click();
  await expect(page.getByText('Closed', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Goals' }).click();
  await expect(page.getByText('Emergency Fund').first()).toBeVisible();

  await page.getByRole('button', { name: 'Create my own account' }).click();
  await expect(page).toHaveURL(/\/auth\/register$/);
});
