import { test as base, expect, request } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export { expect, request };

interface TokenData {
  access: string;
  refresh: string;
  user: unknown;
  access_expires_in: number;
}

const TOKEN_PATH = path.resolve(
  __dirname,
  '..',
  '..',
  '..',
  'test_tokens_clean.json',
);

export function loadTokens(): TokenData {
  const raw = fs.readFileSync(TOKEN_PATH, 'utf-8');
  return JSON.parse(raw);
}

/**
 * Authenticated page fixture.
 * Seeds localStorage with pre-generated JWT tokens so the Vue app
 * initialises auth state without hitting the login API (avoids rate limits).
 */
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    const tokens = loadTokens();
    const expiresAt = Date.now() + tokens.access_expires_in * 1000;

    await page.goto('/login', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    await page.evaluate(
      (data) => {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('token_expires_at', data.expiresAt.toString());
        localStorage.setItem('user', JSON.stringify(data.user));
      },
      {
        access: tokens.access,
        refresh: tokens.refresh,
        expiresAt,
        user: tokens.user,
      },
    );

    await page.reload({ waitUntil: 'domcontentloaded' });

    await page.waitForURL(
      (url) => !url.toString().includes('/login'),
      { timeout: 30000, waitUntil: 'domcontentloaded' },
    );

    await use(page);
  },
});
