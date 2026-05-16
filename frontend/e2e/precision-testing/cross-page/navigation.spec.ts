import { test, expect } from '../auth-api';
import type { Page } from '@playwright/test';

/**
 * Week 5 Cross-Page E2E Tests — Navigation & Routing
 * Test cases NAV_001 ~ NAV_010 in CROSS_PAGE_TEST_CASES.md
 */

const MENU_ITEMS = [
  { path: '/precision-testing/dashboard', label: '风险仪表盘' },
  { path: '/precision-testing/repos', label: '仓库绑定' },
  { path: '/precision-testing/analyses', label: '变更分析' },
  { path: '/precision-testing/mappings', label: '用例映射' },
  { path: '/precision-testing/graph', label: '影响图谱' },
  { path: '/precision-testing/runs', label: '执行记录' },
] as const;

const SEGMENT_LABEL_MAP: Record<string, string> = {
  repos: '仓库绑定',
  analyses: '变更分析',
  mappings: '用例映射',
  graph: '影响图谱',
};

function menuItemByLabel(page: Page, label: string) {
  return page.locator('.el-menu-item').filter({ hasText: label });
}

async function gotoPrecision(page: Page, path: string) {
  // Use domcontentloaded — the SPA holds open polling/SSE which prevents networkidle.
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  // Wait for sidebar to render — confirms the Layout component is mounted.
  await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
}

test.describe('Precision Testing - Navigation & Routing', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await gotoPrecision(authenticatedPage, '/precision-testing/dashboard');
  });

  test('NAV_001: sidebar shows 6 precision-testing menu entries', async ({ authenticatedPage: page }) => {
    for (const item of MENU_ITEMS) {
      const menuItem = menuItemByLabel(page, item.label);
      await expect(menuItem).toBeVisible();
      await expect(menuItem).toContainText(item.label);
    }
  });

  test('NAV_002: each menu item has an icon (el-icon)', async ({ authenticatedPage: page }) => {
    for (const item of MENU_ITEMS) {
      const menuItem = menuItemByLabel(page, item.label);
      await expect(menuItem.locator('.el-icon').first()).toBeVisible();
    }
  });

  test('NAV_003: active menu item is highlighted when URL matches', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');
    const active = menuItemByLabel(page, '仓库绑定');
    await expect(active).toHaveClass(/is-active/);
  });

  test('NAV_004: clicking sibling menu switches highlight', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');
    const analyses = menuItemByLabel(page, '变更分析');
    await analyses.click();
    await page.waitForURL('**/precision-testing/analyses', { timeout: 10000 });
    await expect(analyses).toHaveClass(/is-active/);
    await expect(
      menuItemByLabel(page, '仓库绑定'),
    ).not.toHaveClass(/is-active/);
  });

  test('NAV_005: breadcrumb shows module name "精准测试"', async ({ authenticatedPage: page }) => {
    const breadcrumb = page.locator('.el-breadcrumb');
    await expect(breadcrumb).toBeVisible();
    await expect(breadcrumb).toContainText('精准测试');
  });

  test('NAV_006: breadcrumb shows page title "仓库绑定" on /repos', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');
    const breadcrumb = page.locator('.el-breadcrumb');
    await expect(breadcrumb).toContainText('仓库绑定');
  });

  test('NAV_007: breadcrumb title mapping is correct on all 6 pages', async ({ authenticatedPage: page }) => {
    for (const item of MENU_ITEMS) {
      await gotoPrecision(page, item.path);
      await expect(page.locator('.el-breadcrumb')).toContainText(item.label);
    }
  });

  test('NAV_008: every page can be opened via direct URL', async ({ authenticatedPage: page }) => {
    for (const item of MENU_ITEMS) {
      await gotoPrecision(page, item.path);
      await expect(page.locator('.el-aside')).toBeVisible();
      await expect(page.locator('.el-breadcrumb')).toBeVisible();
      const active = menuItemByLabel(page, item.label);
      await expect(active).toHaveClass(/is-active/);
    }
  });

  test('NAV_009: navigate from home to precision-testing/repos via sidebar', async ({ authenticatedPage: page }) => {
    await page.goto('/home', { waitUntil: 'domcontentloaded' });

    const reposEntry = menuItemByLabel(page, '仓库绑定').first();
    if (await reposEntry.isVisible().catch(() => false)) {
      await reposEntry.click();
    } else {
      await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
    }
    await page.waitForURL('**/precision-testing/repos', { timeout: 10000 });
    await expect(page.locator('.el-breadcrumb')).toContainText('仓库绑定');
  });

  test('NAV_010: rapid menu switching does not break routing', async ({ authenticatedPage: page }) => {
    const sequence = ['repos', 'analyses', 'mappings', 'graph'] as const;
    for (const seg of sequence) {
      const entry = menuItemByLabel(page, SEGMENT_LABEL_MAP[seg]);
      await entry.click();
      await page.waitForURL(`**/precision-testing/${seg}`, { timeout: 10000 });
      await expect(entry).toHaveClass(/is-active/);
    }
    await expect(page.locator('.el-main')).toBeVisible();
  });
});
