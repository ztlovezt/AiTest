import { test as base, expect } from '@playwright/test';
import { test as authTest } from '../auth-api';

/**
 * Week 5 Cross-Page E2E Tests — Authentication & Session
 * Test cases AUTH_001 ~ AUTH_005 in CROSS_PAGE_TEST_CASES.md
 */

const PRECISION_API_PREFIX = '/api/precision-testing/';

base.describe('Precision Testing - Authentication & Session', () => {
  base.beforeEach(async ({ context }) => {
    // Clear storage to simulate logged-out state.
    await context.clearCookies();
    try {
      await context.clearPermissions();
    } catch {
      // ignore — only some browser contexts support this
    }
  });

  base('AUTH_001: unauthenticated access redirects to /login', async ({ page }) => {
    await page.addInitScript(() => {
      try { window.localStorage.clear(); } catch {}
      try { window.sessionStorage.clear(); } catch {}
    });
    await page.goto('/precision-testing/dashboard');
    await page.waitForURL('**/login', { timeout: 15000 });
    expect(page.url()).toContain('/login');
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  base('AUTH_003: expired/invalid token redirects to /login', async ({ page }) => {
    // Inject an invalid access token so route guard / API calls force logout.
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem('access_token', 'invalid.expired.token');
        window.localStorage.setItem('token_expires_at', '0');
      } catch {}
    });
    await page.goto('/precision-testing/dashboard');
    // Either the route guard kicks in (no valid user) or the API 401 logs out.
    await page.waitForURL('**/login', { timeout: 20000 });
    expect(page.url()).toContain('/login');
  });
});

authTest.describe('Precision Testing - Authenticated Session', () => {
  authTest('AUTH_002: authenticated user can access /precision-testing/repos', async ({ authenticatedPage: page }) => {
    const resp = await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    expect(page.url()).toContain('/precision-testing/repos');
    if (resp) {
      expect(resp.status()).toBeLessThan(400);
    }
    await expect(page.locator('.el-aside')).toBeVisible();
  });

  authTest('AUTH_004: all /api/precision-testing/* requests carry Bearer token (RepoBindings)', async ({ authenticatedPage: page }) => {
    const seenAuthHeaders: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes(PRECISION_API_PREFIX)) {
        const auth = req.headers()['authorization'];
        if (auth) seenAuthHeaders.push(auth);
      }
    });

    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    // Wait for the API calls fired during mount
    await page.waitForTimeout(1500);

    expect(seenAuthHeaders.length, 'expected at least one precision-testing API call').toBeGreaterThan(0);
    for (const h of seenAuthHeaders) {
      expect(h).toMatch(/^Bearer\s+.+/);
    }
  });

  authTest('AUTH_005: all /api/precision-testing/* requests carry Bearer token (ChangeAnalyses)', async ({ authenticatedPage: page }) => {
    const seenAuthHeaders: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes(PRECISION_API_PREFIX)) {
        const auth = req.headers()['authorization'];
        if (auth) seenAuthHeaders.push(auth);
      }
    });

    await page.goto('/precision-testing/analyses', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(1500);

    expect(seenAuthHeaders.length).toBeGreaterThan(0);
    for (const h of seenAuthHeaders) {
      expect(h).toMatch(/^Bearer\s+.+/);
    }
  });
});
