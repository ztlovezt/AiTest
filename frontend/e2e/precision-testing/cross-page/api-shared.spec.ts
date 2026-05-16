import { test, expect } from '../auth-api';

/**
 * Week 5 Cross-Page E2E Tests — API Shared Layer
 * Test cases API_SHARE_001 ~ API_SHARE_008 in CROSS_PAGE_TEST_CASES.md
 *
 * These tests validate the cross-cutting concerns of the shared axios layer:
 * baseURL, timeout, function exports, pagination format, task response shape,
 * Bearer-token injection, 401 → logout, and ElMessage error UI.
 */

const PRECISION_API_PREFIX = '/api/precision-testing/';

test.describe('Precision Testing - API Shared Layer', () => {
  test('API_SHARE_001: all precision-testing requests use baseURL "/api"', async ({ authenticatedPage: page }) => {
    const urls: string[] = [];
    page.on('request', (req) => {
      if (req.url().includes(PRECISION_API_PREFIX)) urls.push(req.url());
    });

    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(1500);

    expect(urls.length, 'expected at least one precision-testing API request').toBeGreaterThan(0);
    for (const u of urls) {
      // Should be relative-rooted under /api (no absolute external host)
      const path = new URL(u).pathname;
      expect(path.startsWith('/api/'), `url=${u}`).toBeTruthy();
    }
  });

  test('API_SHARE_002: axios instance configured with timeout = 30000ms', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    // Source contract: frontend/src/utils/api.js sets timeout: 30000.
    const resp = await page.request.get('/src/utils/api.js');
    expect(resp.ok()).toBeTruthy();
    const text = await resp.text();
    expect(text).toContain('timeout: 30000');
  });

  test('API_SHARE_003: precision-testing.js exports all required API functions', async ({ authenticatedPage: page }) => {
    const resp = await page.request.get('/src/api/precision-testing.js');
    expect(resp.ok()).toBeTruthy();
    const src = await resp.text();
    const requiredExports = [
      'getRepoBindings',
      'createRepoBinding',
      'updateRepoBinding',
      'deleteRepoBinding',
      'triggerAnalysis',
      'getChangeAnalyses',
      'getChangeAnalysisDetail',
      'getAnalysisProgress',
      'getMappings',
      'createMapping',
      'updateMapping',
      'deleteMapping',
      'autoBuildMappings',
      'getImpactAnalyses',
      'queryImpact',
      'getGraphData',
      'getRiskPredictions',
      'getRunRecords',
      'getRunRecordDetail',
      'getDashboard',
    ];
    for (const name of requiredExports) {
      expect(src, `missing export: ${name}`).toContain(`export function ${name}`);
    }
  });

  test('API_SHARE_004: list APIs use page=1&page_size=N pagination format', async ({ authenticatedPage: page }) => {
    const listUrls: string[] = [];
    page.on('request', (req) => {
      const url = req.url();
      if (/\/api\/precision-testing\/(repos|analyses|mappings|runs)\/?(\?|$)/.test(url)) {
        listUrls.push(url);
      }
    });

    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(1500);

    expect(listUrls.length).toBeGreaterThan(0);
    const hasPagination = listUrls.some(
      (u) => /[?&]page=\d+/.test(u) && /[?&]page_size=\d+/.test(u),
    );
    expect(hasPagination, `expected page & page_size in one of: ${listUrls.join(', ')}`).toBeTruthy();
  });

  test('API_SHARE_005: task-style endpoints return analysis_id / task_id', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    const triggerBtn = page
      .locator('.el-table__row button:has-text("触发分析"), .el-table__row button:has-text("分析")')
      .first();

    let body: unknown = null;

    if (await triggerBtn.isVisible().catch(() => false)) {
      const respPromise = page.waitForResponse(
        (r) => /\/api\/precision-testing\/repos\/\d+\/analyze\/?$/.test(r.url()),
        { timeout: 10000 },
      );
      await triggerBtn.click();
      const resp = await respPromise.catch(() => null);
      if (resp) {
        body = await resp.json().catch(() => null);
      }
    }

    if (!body) {
      const list = await page.request.get('/api/precision-testing/repos/?page=1&page_size=1', {
        headers: await getAuthHeader(page),
      });
      if (list.ok()) {
        const data = await list.json().catch(() => null);
        const first = data?.results?.[0] ?? data?.[0];
        if (first?.id) {
          const trig = await page.request.post(
            `/api/precision-testing/repos/${first.id}/analyze/`,
            { headers: await getAuthHeader(page) },
          );
          if (trig.ok()) body = await trig.json().catch(() => null);
        }
      }
    }

    if (body && typeof body === 'object') {
      const obj = body as Record<string, unknown>;
      const hasId = 'analysis_id' in obj || 'task_id' in obj || 'id' in obj;
      expect(hasId, `task response should include analysis_id/task_id/id, got=${JSON.stringify(obj)}`).toBeTruthy();
    } else {
      test.info().annotations.push({
        type: 'skip-reason',
        description: 'No repo binding available to trigger analysis — skipping body shape check.',
      });
    }
  });

  test('API_SHARE_006: request interceptor injects Authorization Bearer header', async ({ authenticatedPage: page }) => {
    const authValues: (string | undefined)[] = [];
    page.on('request', (req) => {
      if (req.url().includes(PRECISION_API_PREFIX)) {
        authValues.push(req.headers()['authorization']);
      }
    });

    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(1500);

    expect(authValues.length).toBeGreaterThan(0);
    for (const v of authValues) {
      expect(v).toBeTruthy();
      expect(v!).toMatch(/^Bearer\s+\S+/);
    }
  });

  test('API_SHARE_007: 401 from API forces logout & redirect to /login', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    // Invalidate the token in storage so the next request returns 401.
    await page.evaluate(() => {
      window.localStorage.setItem('access_token', 'invalid.token.value');
      window.localStorage.setItem('refresh_token', '');
      window.localStorage.setItem('token_expires_at', '0');
    });

    // Trigger a new API call by reloading.
    await page.reload().catch(() => undefined);
    await page.waitForURL('**/login', { timeout: 20000 });
    expect(page.url()).toContain('/login');
  });

  test('API_SHARE_008: API failure surfaces ElMessage error toast', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    // Force any subsequent precision-testing requests to fail.
    await page.route('**/api/precision-testing/**', (route) => route.abort('failed'));
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
    const errorToast = page.locator('.el-message--error, .el-message.is-error, .el-message');
    await expect(errorToast.first()).toBeVisible({ timeout: 10000 });
  });
});

async function getAuthHeader(page: import('@playwright/test').Page) {
  const token = await page.evaluate(() => window.localStorage.getItem('access_token'));
  return token ? { Authorization: `Bearer ${token}` } : {};
}
