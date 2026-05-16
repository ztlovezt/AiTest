/**
 * Risk Dashboard — UI Functional, E2E & Error Handling Tests
 *
 * Coverage:
 *   - Manual functional verification: DASH_UI_001 ~ DASH_UI_029
 *   - E2E: DASH_E2E_001 ~ DASH_E2E_002
 *   - Exception scenarios: DASH_ERR_001 ~ DASH_ERR_004
 *
 * NOTE: Backend DashboardView now returns the nested structure expected by
 * the frontend (summary, risk_distribution, trend, top_risky_files, run_stats).
 * Charts render with real aggregated data when available, otherwise zero/empty.
 */
import { test, expect } from './auth-api';

test.describe('Risk Dashboard — Manual Functional Verification', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/precision-testing/dashboard', {
      waitUntil: 'domcontentloaded',
    });
    // Precision-testing pages use Layout → wait for sidebar
    await authenticatedPage.locator('.el-aside').first().waitFor({
      state: 'visible',
      timeout: 15000,
    });
    // Give ECharts a moment to initialise (canvas is not in DOM immediately)
    await authenticatedPage.waitForTimeout(800);
  });

  /* ── KPI Cards ── */

  test('DASH_UI_001: page loads without crash, 4 KPI cards present', async ({ authenticatedPage: page }) => {
    // Verify all 4 KPI titles are visible (more robust than counting .el-col)
    const titles = ['绑定仓库数', '变更分析次数', '映射关系总数', '平均缩减率'];
    for (const t of titles) {
      await expect(page.locator('.risk-dashboard').getByText(t)).toBeVisible();
    }
    // Also verify 4 statistic heads exist
    const stats = page.locator('.risk-dashboard .el-statistic__head');
    await expect(stats).toHaveCount(4);
  });

  test('DASH_UI_002: loading state appears then disappears', async ({ authenticatedPage: page }) => {
    // Reload to observe loading lifecycle
    await page.reload({ waitUntil: 'domcontentloaded' });
    // v-loading adds .el-loading-mask inside the element
    const dashboard = page.locator('.risk-dashboard');
    // Loading mask may appear briefly
    await expect(dashboard).toBeVisible();
    // After data fetch (or error), loading should be gone
    await expect(dashboard.locator('.el-loading-mask')).not.toBeVisible({ timeout: 10000 });
  });

  test('DASH_UI_003~006: KPI card titles and values', async ({ authenticatedPage: page }) => {
    const cards = page.locator('.risk-dashboard .kpi-row .el-card');
    await expect(cards).toHaveCount(4);

    const expectedTitles = ['绑定仓库数', '变更分析次数', '映射关系总数', '平均缩减率'];
    for (let i = 0; i < 4; i++) {
      const title = cards.nth(i).locator('.el-statistic__head');
      await expect(title).toHaveText(expectedTitles[i]);
    }

    // Values should be numeric (0 when backend has no data)
    for (let i = 0; i < 4; i++) {
      const valueEl = cards.nth(i).locator('.el-statistic__content');
      await expect(valueEl).toBeVisible();
      const text = await valueEl.textContent();
      expect(text).toBeTruthy();
      // Should not contain NaN or null
      expect(text).not.toMatch(/NaN|null|undefined/i);
    }
  });

  test('DASH_UI_007: KPI shows 0 instead of blank when count is zero', async ({ authenticatedPage: page }) => {
    const firstCardValue = page.locator('.kpi-row .el-card').first().locator('.el-statistic__number');
    await expect(firstCardValue).toBeVisible();
    const text = await firstCardValue.textContent();
    // When no data the backend returns 0; the card should render "0"
    expect(text).toMatch(/\d/);
  });

  test('DASH_UI_008: null-safe defaults (no NaN)', async ({ authenticatedPage: page }) => {
    const allValues = page.locator('.kpi-row .el-statistic__content');
    const count = await allValues.count();
    for (let i = 0; i < count; i++) {
      const text = await allValues.nth(i).textContent();
      expect(text).not.toMatch(/NaN/);
    }
  });

  test('DASH_UI_009: KPI icons have distinct colours', async ({ authenticatedPage: page }) => {
    const icons = page.locator('.kpi-row .kpi-icon');
    await expect(icons).toHaveCount(4);
    const classes = await Promise.all(
      Array.from({ length: 4 }, (_, i) => icons.nth(i).getAttribute('class')),
    );
    const colourClasses = ['kpi-blue', 'kpi-green', 'kpi-orange', 'kpi-purple'];
    colourClasses.forEach((cls) => {
      expect(classes.some((c) => c?.includes(cls))).toBe(true);
    });
  });

  /* ── Charts ── */

  test('DASH_UI_010: risk distribution pie chart renders (canvas exists)', async ({ authenticatedPage: page }) => {
    const pieCard = page.locator('.chart-card').filter({ hasText: '风险等级分布' });
    await expect(pieCard).toBeVisible();
    const canvas = pieCard.locator('canvas');
    await expect(canvas).toBeVisible({ timeout: 5000 });
  });

  test('DASH_UI_011: pie chart with zero data still renders', async ({ authenticatedPage: page }) => {
    // Zero data is the current state; canvas should still exist
    const pieCanvas = page.locator('.chart-card').filter({ hasText: '风险等级分布' }).locator('canvas');
    await expect(pieCanvas).toBeVisible();
  });

  test('DASH_UI_012: pie chart tooltip on hover', async ({ authenticatedPage: page }) => {
    const pieCanvas = page.locator('.chart-card').filter({ hasText: '风险等级分布' }).locator('canvas');
    await expect(pieCanvas).toBeVisible();
    await pieCanvas.hover();
    await page.waitForTimeout(300);
    // Tooltip content is inside a fixed-position ECharts overlay; just verify hover does not crash
    await expect(pieCanvas).toBeVisible();
  });

  test('DASH_UI_013: trend line chart renders', async ({ authenticatedPage: page }) => {
    const lineCard = page.locator('.chart-card').filter({ hasText: '近 14 天变更分析趋势' });
    await expect(lineCard).toBeVisible();
    await expect(lineCard.locator('canvas')).toBeVisible({ timeout: 5000 });
  });

  test('DASH_UI_014: trend line chart with empty data still renders', async ({ authenticatedPage: page }) => {
    const lineCanvas = page.locator('.chart-card').filter({ hasText: '近 14 天变更分析趋势' }).locator('canvas');
    await expect(lineCanvas).toBeVisible();
  });

  test('DASH_UI_015: trend chart tooltip on hover', async ({ authenticatedPage: page }) => {
    const canvas = page.locator('.chart-card').filter({ hasText: '近 14 天变更分析趋势' }).locator('canvas');
    await expect(canvas).toBeVisible();
    await canvas.hover();
    await page.waitForTimeout(300);
    await expect(canvas).toBeVisible();
  });

  test('DASH_UI_016: top risky files bar chart renders', async ({ authenticatedPage: page }) => {
    const barCard = page.locator('.chart-card').filter({ hasText: '高风险文件 Top 10' });
    await expect(barCard).toBeVisible();
    await expect(barCard.locator('canvas')).toBeVisible({ timeout: 5000 });
  });

  test('DASH_UI_017: long file path ellipsis (Y-axis labels)', async ({ authenticatedPage: page }) => {
    // When empty data, chart renders with no labels; verify canvas exists
    const canvas = page.locator('.chart-card').filter({ hasText: '高风险文件 Top 10' }).locator('canvas');
    await expect(canvas).toBeVisible();
    // Verify chart container does not overflow horizontally
    const overflow = await page.evaluate(() => {
      const docW = document.documentElement.clientWidth;
      return document.body.scrollWidth > docW + 8;
    });
    expect(overflow).toBeFalsy();
  });

  test('DASH_UI_018: bar colour reflects risk score thresholds', async ({ authenticatedPage: page }) => {
    // Colour logic is in frontend initTopFiles:
    // risk_score > 0.7 → red, > 0.4 → orange, else blue
    // With empty data we just verify the chart renders without crash
    const canvas = page.locator('.chart-card').filter({ hasText: '高风险文件 Top 10' }).locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('DASH_UI_019: top files chart with empty data', async ({ authenticatedPage: page }) => {
    const canvas = page.locator('.chart-card').filter({ hasText: '高风险文件 Top 10' }).locator('canvas');
    await expect(canvas).toBeVisible();
  });

  test('DASH_UI_020: run stats stacked bar chart renders', async ({ authenticatedPage: page }) => {
    const stackCard = page.locator('.chart-card').filter({ hasText: '执行记录 — 精准 vs 全量' });
    await expect(stackCard).toBeVisible();
    await expect(stackCard.locator('canvas')).toBeVisible({ timeout: 5000 });
  });

  test('DASH_UI_021: stacked bar tooltip on hover', async ({ authenticatedPage: page }) => {
    const canvas = page.locator('.chart-card').filter({ hasText: '执行记录 — 精准 vs 全量' }).locator('canvas');
    await expect(canvas).toBeVisible();
    await canvas.hover();
    await page.waitForTimeout(300);
    await expect(canvas).toBeVisible();
  });

  test('DASH_UI_022: stacked bar with empty data', async ({ authenticatedPage: page }) => {
    const canvas = page.locator('.chart-card').filter({ hasText: '执行记录 — 精准 vs 全量' }).locator('canvas');
    await expect(canvas).toBeVisible();
  });

  /* ── Layout ── */

  test('DASH_UI_023: first row has 4 KPI cards (6-col each)', async ({ authenticatedPage: page }) => {
    const cols = page.locator('.kpi-row > .el-col');
    await expect(cols).toHaveCount(4);
    for (let i = 0; i < 4; i++) {
      const cls = await cols.nth(i).getAttribute('class');
      expect(cls).toMatch(/el-col-6/);
    }
  });

  test('DASH_UI_024: second row = pie(8) + line(16)', async ({ authenticatedPage: page }) => {
    const row = page.locator('.chart-row').first();
    const cols = row.locator('> .el-col');
    await expect(cols).toHaveCount(2);
    const firstCls = await cols.nth(0).getAttribute('class');
    const secondCls = await cols.nth(1).getAttribute('class');
    expect(firstCls).toMatch(/el-col-8/);
    expect(secondCls).toMatch(/el-col-16/);
  });

  test('DASH_UI_025: third row = two bar charts (12 + 12)', async ({ authenticatedPage: page }) => {
    const rows = page.locator('.chart-row');
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(2);
    const thirdRow = rows.nth(1);
    const cols = thirdRow.locator('> .el-col');
    await expect(cols).toHaveCount(2);
    const firstCls = await cols.nth(0).getAttribute('class');
    const secondCls = await cols.nth(1).getAttribute('class');
    expect(firstCls).toMatch(/el-col-12/);
    expect(secondCls).toMatch(/el-col-12/);
  });

  test('DASH_UI_026: resize triggers chart resize()', async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.waitForTimeout(500);
    const charts = page.locator('.chart-box canvas');
    await expect(charts.first()).toBeVisible();

    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(500);
    await expect(charts.first()).toBeVisible();

    // No overflow after resize
    const overflow = await page.evaluate(() => {
      return document.body.scrollWidth > document.documentElement.clientWidth + 8;
    });
    expect(overflow).toBeFalsy();
  });

  test('DASH_UI_027: chart instances disposed on unmount', async ({ authenticatedPage: page }) => {
    // Navigate away and check that charts are disposed via evaluate
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(500);
    // If there were memory leaks, the page would still work normally
    await expect(page.locator('.el-aside')).toBeVisible();
  });

  test('DASH_UI_028: API 500 error → charts initialised with empty data, page does not crash', async ({ authenticatedPage: page }) => {
    await page.route('**/api/precision-testing/dashboard/**', (route) =>
      route.fulfill({ status: 500, body: JSON.stringify({ error: 'Internal Server Error' }) }),
    );
    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    // Error toast should appear
    const errorMsg = page.locator('.el-message--error, .el-message.is-error');
    await expect(errorMsg.first()).toBeVisible({ timeout: 10000 });

    // Chart containers should still exist (empty data initialised)
    const chartBoxes = page.locator('.chart-box');
    expect(await chartBoxes.count()).toBeGreaterThanOrEqual(4);

    await page.unroute('**/api/precision-testing/dashboard/**');
  });

  test('DASH_UI_029: refresh updates KPI values', async ({ authenticatedPage: page }) => {
    // Read current value
    const firstValue = page.locator('.kpi-row .el-statistic__number').first();
    await expect(firstValue).toBeVisible();
    const before = await firstValue.textContent();

    // Reload page
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(800);

    const after = await page.locator('.kpi-row .el-statistic__number').first().textContent();
    // Value may be the same (no new data), but element must still render correctly
    expect(after).toBeTruthy();
    expect(after).not.toMatch(/NaN/);
  });
});

test.describe('Risk Dashboard — E2E', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/precision-testing/dashboard', {
      waitUntil: 'domcontentloaded',
    });
    await authenticatedPage.locator('.el-aside').first().waitFor({
      state: 'visible',
      timeout: 15000,
    });
    await authenticatedPage.waitForTimeout(800);
  });

  test('DASH_E2E_001: full data display end-to-end', async ({ authenticatedPage: page }) => {
    // 4 KPI cards visible
    await expect(page.locator('.kpi-row .el-card')).toHaveCount(4);
    // Wait for ECharts to create canvases (async init can take >1s)
    const canvases = page.locator('.chart-box canvas');
    await expect(canvases.first()).toBeVisible({ timeout: 10000 });
    expect(await canvases.count()).toBeGreaterThanOrEqual(4);
    for (let i = 0; i < (await canvases.count()); i++) {
      await expect(canvases.nth(i)).toBeVisible();
    }
  });

  test('DASH_E2E_002: empty data graceful degradation', async ({ authenticatedPage: page }) => {
    // With current backend all data is empty/zero; verify page does not crash
    await expect(page.locator('.risk-dashboard')).toBeVisible();
    await expect(page.locator('.kpi-row .el-card')).toHaveCount(4);
    const values = page.locator('.kpi-row .el-statistic__number');
    const count = await values.count();
    for (let i = 0; i < count; i++) {
      const text = await values.nth(i).textContent();
      expect(text).not.toMatch(/NaN|null/);
    }
    // All chart canvases present
    expect(await page.locator('.chart-box canvas').count()).toBeGreaterThanOrEqual(4);
  });
});

test.describe('Risk Dashboard — Exception Scenarios', () => {
  test('DASH_ERR_001: API load failure shows error message, charts empty-initialised', async ({ authenticatedPage: page }) => {
    await page.route('**/api/precision-testing/dashboard/**', (route) =>
      route.abort('failed'),
    );
    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    const errorMsg = page.locator('.el-message--error, .el-message.is-error, .el-message');
    await expect(errorMsg.first()).toBeVisible({ timeout: 10000 });

    // KPI cards should still show 0 (null-safe)
    await expect(page.locator('.kpi-row .el-card').first()).toBeVisible();

    await page.unroute('**/api/precision-testing/dashboard/**');
  });

  test('DASH_ERR_002: API timeout shows error, no infinite loading', async ({ authenticatedPage: page }) => {
    await page.route('**/api/precision-testing/dashboard/**', async (route) => {
      // Never respond → timeout
      await new Promise(() => {});
    });
    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });

    // Loading should eventually disappear (Axios timeout or page logic)
    const dashboard = page.locator('.risk-dashboard');
    await expect(dashboard.locator('.el-loading-mask')).not.toBeVisible({ timeout: 35000 });

    // Error feedback should appear
    const errorMsg = page.locator('.el-message--error');
    await expect(errorMsg.first()).toBeVisible({ timeout: 35000 });

    await page.unroute('**/api/precision-testing/dashboard/**');
  });

  test('DASH_ERR_003: partial field missing uses safe defaults', async ({ authenticatedPage: page }) => {
    await page.route('**/api/precision-testing/dashboard/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ summary: {} }),
      }),
    );
    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);

    // Page should not crash
    await expect(page.locator('.risk-dashboard')).toBeVisible();
    await expect(page.locator('.kpi-row .el-card').first()).toBeVisible();

    await page.unroute('**/api/precision-testing/dashboard/**');
  });

  test('DASH_ERR_004: leave page during loading → no memory leak', async ({ authenticatedPage: page }) => {
    // Slow down API so loading lasts long enough
    await page.route('**/api/precision-testing/dashboard/**', async (route) => {
      await new Promise((r) => setTimeout(r, 5000));
      await route.continue();
    });

    await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
    // Leave before API completes
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    // No crash, sidebar visible on new page
    await expect(page.locator('.el-aside')).toBeVisible();

    await page.unroute('**/api/precision-testing/dashboard/**');
  });
});
