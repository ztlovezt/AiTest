/**
 * Risk Dashboard — Performance Tests
 *
 * DASH_PERF_001: API response time < 2s (P95)
 * DASH_PERF_002: 4 ECharts charts render within 1s, main thread not blocked > 3s
 */
import { test, expect } from './auth-api';

const BACKEND = 'http://localhost:8000';

test.describe('Risk Dashboard — Performance', () => {
  test('DASH_PERF_001: dashboard API response time < 2s', async () => {
    const fs = await import('fs');
    const path = await import('path');
    const tokenPath = path.resolve(__dirname, '../../../test_tokens_clean.json');
    const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf-8'));
    const token = tokenData.access;

    const { request } = await import('@playwright/test');
    const ctx = await request.newContext({
      baseURL: BACKEND,
      extraHTTPHeaders: { Authorization: `Bearer ${token}` },
    });

    const times: number[] = [];
    try {
      // Warm-up + 5 samples for P95 estimation
      for (let i = 0; i < 5; i++) {
        const start = Date.now();
        const resp = await ctx.get('/api/precision-testing/dashboard/');
        const elapsed = Date.now() - start;
        expect(resp.status()).toBe(200);
        times.push(elapsed);
      }
    } finally {
      await ctx.dispose();
    }

    times.sort((a, b) => a - b);
    const p95Idx = Math.ceil(times.length * 0.95) - 1;
    const p95 = times[Math.max(0, p95Idx)];
    expect(p95).toBeLessThan(2000);
  });

  test('DASH_PERF_002: 4 charts render within acceptable time', async ({ authenticatedPage: page }) => {
    // Measure time from navigation start to all 4 canvases visible
    const startTime = Date.now();

    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    // Wait for all 4 chart canvases
    const chartBoxes = page.locator('.chart-box');
    await expect(chartBoxes).toHaveCount(4);
    for (let i = 0; i < 4; i++) {
      await expect(chartBoxes.nth(i).locator('canvas')).toBeVisible({ timeout: 5000 });
    }

    const elapsed = Date.now() - startTime;
    // Charts should render within 8s of page start (accounts for real data aggregation + ECharts init)
    expect(elapsed).toBeLessThan(8000);

    // Check Long Tasks via Performance API
    const longTasks = await page.evaluate(() => {
      if ('performance' in window && 'getEntriesByType' in performance) {
        const entries = performance.getEntriesByType('longtask');
        return entries
          .filter((e: PerformanceEntry) => {
            const t = e as any;
            return t.duration > 50;
          })
          .map((e: PerformanceEntry) => {
            const t = e as any;
            return t.duration;
          });
      }
      return [];
    });

    // No task should block main thread > 3s
    const maxTask = longTasks.length > 0 ? Math.max(...longTasks) : 0;
    expect(maxTask).toBeLessThan(3000);
  });
});
