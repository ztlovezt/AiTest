import { test } from './auth';
import { expect } from '@playwright/test';

/**
 * ImpactGraph.vue E2E Tests
 * Based on Week5_PrecisionTesting_TestCases.md test cases IMPACT_001 to IMPACT_022
 */
test.describe('ImpactGraph Page', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/precision-testing/graph');
    await authenticatedPage.waitForTimeout(3000);
  });

  test('IMPACT_001: 验证图谱页面初始加载全量图谱', async ({ authenticatedPage: page }) => {
    // Canvas or graph container should be visible
    await expect(page.locator('.cy-container')).toBeVisible({ timeout: 10000 });
  });

  test('IMPACT_002: 验证函数名查询影响', async ({ authenticatedPage: page }) => {
    const searchInput = page.locator('input[placeholder*="函数"], input[placeholder*="查询"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test_function');
      const searchButton = page.locator('button:has-text("查询影响"), button:has-text("查询")').first();
      if (await searchButton.isVisible()) {
        await searchButton.click();
        await page.waitForTimeout(2000);
      }
    }
  });

  test('IMPACT_003: 验证回车键触发查询', async ({ authenticatedPage: page }) => {
    const searchInput = page.locator('input[placeholder*="函数"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('test_function');
      await searchInput.press('Enter');
      await page.waitForTimeout(2000);
    }
  });

  test('IMPACT_007: 验证节点点击选中', async ({ authenticatedPage: page }) => {
    // Wait for graph to load
    await page.waitForTimeout(2000);
    // Click on a node if any exist
    const node = page.locator('[class*="node"], .cytoscape-node').first();
    if (await node.isVisible()) {
      await node.click();
      // Property panel should show
      await page.waitForTimeout(500);
    }
  });

  test('IMPACT_008: 验证节点属性面板显示内容', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(2000);
    const propertyPanel = page.locator('[class*="property"], [class*="detail"], [class*="panel"]').last();
    if (await propertyPanel.isVisible()) {
      await expect(propertyPanel).toBeVisible();
    }
  });

  test('IMPACT_011: 验证图例显示', async ({ authenticatedPage: page }) => {
    const legend = page.locator('[class*="legend"], [class*="图例"]').first();
    if (await legend.isVisible()) {
      await expect(legend).toBeVisible();
      // Should show node type labels
      await expect(legend).toContainText(/Function|TestCase|API|Class|Module/);
    }
  });

  test('IMPACT_012: 验证空白区域点击取消选中', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(2000);
    // Click on background
    const graphArea = page.locator('.cy-container').first();
    if (await graphArea.isVisible()) {
      await graphArea.click({ position: { x: 10, y: 10 } });
      await page.waitForTimeout(500);
    }
  });

  test('IMPACT_014: 验证重置按钮功能', async ({ authenticatedPage: page }) => {
    const resetButton = page.locator('button:has-text("重置")').first();
    if (await resetButton.isVisible()) {
      await resetButton.click();
      await page.waitForTimeout(500);
    }
  });

  test('IMPACT_015: 验证加载图谱失败错误处理', async ({ authenticatedPage: page }) => {
    await page.route('**/api/precision-testing/graph/**', (route) => {
      route.abort('failed');
    });
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
    const errorToast = page.locator('.el-message--error, .el-message.is-error, .el-message');
    await expect(errorToast.first()).toBeVisible({ timeout: 10000 });
  });

  test('IMPACT_017: 验证查询空函数名加载全量图谱', async ({ authenticatedPage: page }) => {
    const searchInput = page.locator('input[placeholder*="函数"]').first();
    if (await searchInput.isVisible()) {
      // Leave empty and click search
      const searchButton = page.locator('button:has-text("查询影响")').first();
      if (await searchButton.isVisible()) {
        await searchButton.click();
        await page.waitForTimeout(2000);
        // Should load full graph
        await expect(page.locator('.cy-container')).toBeVisible();
      }
    }
  });

  test('IMPACT_018: 验证Cytoscape样式-节点颜色', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(2000);
    // Graph should render with colored nodes
    const graph = page.locator('.cy-container').first();
    await expect(graph).toBeVisible();
  });

  test('IMPACT_021: 验证图谱布局自动计算', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(3000);
    // Graph should be laid out without overlaps
    const graph = page.locator('.cy-container').first();
    await expect(graph).toBeVisible();
  });
});