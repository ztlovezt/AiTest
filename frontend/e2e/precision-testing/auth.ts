import { test as base } from '@playwright/test';

// Extend test with authenticated state - does NOT re-export expect
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    const username = process.env.E2E_USERNAME || 'admin';
    const password = process.env.E2E_PASSWORD || 'admin123456';

    // Cache token per worker to avoid rate limits
    if (!(globalThis as Record<string, unknown>).__e2eAuthCache) {
      const loginResp = await page.request.post('http://localhost:8000/api/auth/login/', {
        data: { username, password },
        headers: { 'Content-Type': 'application/json' },
      });

      if (!loginResp.ok()) {
        const text = await loginResp.text();
        throw new Error(`Login API failed: ${loginResp.status()} ${text}`);
      }

      const loginData = await loginResp.json();
      (globalThis as Record<string, unknown>).__e2eAuthCache = {
        access: loginData.access,
        refresh: loginData.refresh,
        expiresAt: Date.now() + (loginData.access_expires_in || 15 * 60) * 1000,
        user: loginData.user,
      };
    }

    const cached = (globalThis as Record<string, unknown>).__e2eAuthCache as {
      access: string;
      refresh: string;
      expiresAt: number;
      user: unknown;
    };

    await page.goto('/login', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.evaluate(
      (data: { access: string; refresh: string; expiresAt: number; user: unknown }) => {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('token_expires_at', data.expiresAt.toString());
        localStorage.setItem('user', JSON.stringify(data.user));
      },
      cached,
    );

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20000 });

    await use(page);
  },
});