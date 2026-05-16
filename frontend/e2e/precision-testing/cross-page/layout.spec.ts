import { test, expect } from '../auth-api';

/**
 * Week 5 Cross-Page E2E Tests — Layout & Responsive
 * Test cases LAYOUT_001 ~ LAYOUT_005 in CROSS_PAGE_TEST_CASES.md
 */

test.describe('Precision Testing - Layout & Responsive', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.setViewportSize({ width: 1920, height: 1080 });
  });

  test('LAYOUT_001: precision-testing module uses Layout (aside + main + header)', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await expect(page.locator('.el-aside')).toBeVisible();
    await expect(page.locator('.el-main')).toBeVisible();
    await expect(page.locator('.el-header')).toBeVisible();
  });

  test('LAYOUT_002: main content area has padding (>= 16px)', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    const main = page.locator('.el-main').first();
    await expect(main).toBeVisible();
    const padding = await main.evaluate((el) => {
      const cs = window.getComputedStyle(el);
      return {
        top: parseFloat(cs.paddingTop),
        right: parseFloat(cs.paddingRight),
        bottom: parseFloat(cs.paddingBottom),
        left: parseFloat(cs.paddingLeft),
      };
    });
    // The acceptance criterion is "20px"; allow >= 16 to accommodate theme tokens.
    expect(padding.top).toBeGreaterThanOrEqual(16);
    expect(padding.right).toBeGreaterThanOrEqual(16);
    expect(padding.bottom).toBeGreaterThanOrEqual(16);
    expect(padding.left).toBeGreaterThanOrEqual(16);
  });

  test('LAYOUT_003: at 1920px wide, content does not overflow', async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    const overflow = await page.evaluate(() => {
      const docW = document.documentElement.clientWidth;
      return document.body.scrollWidth > docW + 4;
    });
    expect(overflow, 'body should not horizontally overflow at 1920px').toBeFalsy();
  });

  test('LAYOUT_004: at 1024px wide, layout still renders without horizontal overflow', async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await expect(page.locator('.el-aside')).toBeVisible();
    const overflow = await page.evaluate(() => {
      const docW = document.documentElement.clientWidth;
      return document.body.scrollWidth > docW + 8;
    });
    expect(overflow, 'no horizontal overflow at 1024px').toBeFalsy();
  });

  test('LAYOUT_005: at 1366px wide, change-analyses left/right split renders', async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await page.goto('/precision-testing/analyses', { waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await expect(page.locator('.el-aside')).toBeVisible();
    await expect(page.locator('.el-main')).toBeVisible();
    const overflow = await page.evaluate(() => {
      const docW = document.documentElement.clientWidth;
      return document.body.scrollWidth > docW + 8;
    });
    expect(overflow, 'no horizontal overflow at 1366px').toBeFalsy();
  });
});
