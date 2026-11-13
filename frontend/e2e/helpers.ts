import { createHmac } from 'node:crypto';

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

const MAILPIT = process.env['MAILPIT_URL'] ?? 'http://localhost:8025';

/**
 * The link in the latest email to this address (Mailpit's API), pointed at the
 * app under test: emails link to the Compose web app, the tests may run elsewhere.
 */
export async function emailedLink(page: Page, to: string, subject: string): Promise<string> {
  let link: string | undefined;
  await expect
    .poll(
      async () => {
        const search = await page.request.get(`${MAILPIT}/api/v1/search`, {
          params: { query: `to:"${to}" subject:"${subject}"` },
        });
        const [latest] = (await search.json()).messages ?? [];
        if (!latest) return null;
        const message = await (
          await page.request.get(`${MAILPIT}/api/v1/message/${latest.ID}`)
        ).json();
        link = /https?:\/\/\S+/.exec(message.Text)?.[0];
        return link ?? null;
      },
      { timeout: 15_000 },
    )
    .not.toBeNull();
  const url = new URL(link!);
  return url.pathname + url.search;
}

/** Creates the current month from the empty month screen. */
export async function createCurrentMonth(page: Page): Promise<void> {
  const title = currentMonthTitle();
  await page.getByRole('button', { name: `Create ${title}` }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('button', { name: `Create ${title}` }).click();
  await expect(page.getByRole('heading', { level: 1, name: title })).toBeVisible();
}

/** The TOTP code (RFC 6238, SHA-1, 6 digits, 30 s) for a base32 secret, `offset` steps away. */
export function totp(secret: string, offset = 0, now = Date.now()): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const char of secret.replace(/=+$/, '').toUpperCase()) {
    bits += alphabet.indexOf(char).toString(2).padStart(5, '0');
  }
  const key = Buffer.from(bits.match(/.{8}/g)!.map((byte) => parseInt(byte, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(now / 30_000) + offset));
  const hmac = createHmac('sha1', key).update(counter).digest();
  const start = hmac[hmac.length - 1]! & 0x0f;
  const value = (hmac.readUInt32BE(start) & 0x7fffffff) % 1_000_000;
  return value.toString().padStart(6, '0');
}
