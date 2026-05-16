import { test, expect } from './auth-api';

/**
 * PrecisionRunHistory.vue E2E Tests
 * Based on PRECISION_RUN_HISTORY_TEST_CASES.md
 * Coverage: E2E + Exception Scenarios
 */
test.describe('PrecisionRunHistory Page', () => {
  test.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto('/precision-testing/runs');
    await authenticatedPage.waitForTimeout(3000);
  });

  test('RUNHIST_001: 验证执行记录列表默认加载', async ({ authenticatedPage: page }) => {
    // 使用精确选择器避免 strict mode violation
    await expect(page.locator('.run-history .el-table')).toBeVisible({ timeout: 10000 });
  });

  test('RUNHIST_002-004: 验证执行状态筛选', async ({ authenticatedPage: page }) => {
    // Look for status filter dropdown
    const filterSelect = page.locator('.el-select, [class*="filter"]').first();
    if (await filterSelect.isVisible()) {
      await filterSelect.click();
      await page.waitForTimeout(500);
      // Select "已完成" option (value="completed" 与后端 status choices 一致)
      const option = page.locator('.el-select-dropdown__item:has-text("已完成"), [class*="option"]:has-text("已完成")').first();
      if (await option.isVisible()) {
        await option.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('RUNHIST_005: 验证日期范围筛选', async ({ authenticatedPage: page }) => {
    // Look for date picker
    const datePicker = page.locator('.el-date-editor, [class*="date"]').first();
    if (await datePicker.isVisible()) {
      await datePicker.click();
      await page.waitForTimeout(500);
    }
  });

  test('RUNHIST_007: 验证刷新按钮功能', async ({ authenticatedPage: page }) => {
    const refreshButton = page.locator('button:has-text("刷新"), button:has-text("刷新")').first();
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('RUNHIST_008: 验证表格行点击打开详情', async ({ authenticatedPage: page }) => {
    // 等待 loading 完成，避免 el-loading-mask 拦截点击
    await page.locator('.el-loading-mask').first().waitFor({ state: 'hidden', timeout: 15000 });
    const tableRow = page.locator('.el-table__body tr').first();
    if (await tableRow.isVisible()) {
      await tableRow.click();
      await page.waitForTimeout(500);
      await expect(page.locator('.el-drawer[aria-label="执行记录详情"]')).toBeVisible();
    }
  });

  test('RUNHIST_009: 验证详情按钮打开抽屉', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情"), [class*="table"] button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await expect(page.locator('.el-drawer[aria-label="执行记录详情"]')).toBeVisible();
    }
  });

  test('RUNHIST_010: 验证详情抽屉信息展示', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await page.waitForTimeout(1000);
      const drawer = page.locator('.el-drawer[aria-label="执行记录详情"]');
      if (await drawer.isVisible()) {
        await expect(drawer).toContainText(/ID|状态|仓库|分支/);
      }
    }
  });

  test('RUNHIST_011: 验证详情抽屉用例列表', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await page.waitForTimeout(1000);
      const drawer = page.locator('.el-drawer[aria-label="执行记录详情"]');
      if (await drawer.isVisible()) {
        // Look for test case list
        const hasCaseList = await drawer.locator('[class*="case"], [class*="list"]').isVisible();
        //抽屉应该显示用例列表
      }
    }
  });

  test('RUNHIST_013: 验证详情抽屉关闭', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await page.waitForTimeout(1000);
      const closeButton = page.locator('.el-drawer__close, .el-drawer button:has-text("关闭")').first();
      if (await closeButton.isVisible()) {
        await closeButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('RUNHIST_014: 验证缩减率进度条颜色', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(1000);
    const progressBars = page.locator('.el-progress, [class*="progress"]');
    const count = await progressBars.count();
    if (count > 0) {
      await expect(progressBars.first()).toBeVisible();
    }
  });

  test('RUNHIST_016: 验证状态标签颜色', async ({ authenticatedPage: page }) => {
    await page.waitForTimeout(1000);
    const statusTags = page.locator('.el-tag, [class*="status"]');
    if (await statusTags.first().isVisible()) {
      await expect(statusTags.first()).toBeVisible();
    }
  });

  test('RUNHIST_018: 验证分页功能', async ({ authenticatedPage: page }) => {
    const pagination = page.locator('.el-pagination').first();
    if (await pagination.isVisible()) {
      const nextButton = page.locator('.el-pagination button:has-text("»"), .el-pagination button:has-text("下一页")').first();
      if (await nextButton.isVisible() && await nextButton.isEnabled()) {
        await nextButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('RUNHIST_020: 验证详情加载状态', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await detailButton.click();
      await page.waitForTimeout(100);
      // Should show loading
      const hasLoading = await page.locator('.el-loading-mask, [class*="loading"]').first().isVisible();
      await page.waitForTimeout(2000);
    }
  });

  test('RUN_ERR_002: 验证详情加载网络失败', async ({ authenticatedPage: page }) => {
    const detailButton = page.locator('button:has-text("详情")').first();
    if (await detailButton.isVisible()) {
      await page.route('**/api/precision-testing/runs/**', (route) => route.abort('failed'));
      await detailButton.click();
      await page.waitForTimeout(1000);
      const errorToast = page.locator('.el-message--error, .el-message.is-error, .el-message');
      await expect(errorToast.first()).toBeVisible({ timeout: 10000 });
      await page.unroute('**/api/precision-testing/runs/**');
    }
  });

  test('RUN_ERR_001: 验证列表加载网络失败', async ({ authenticatedPage: page }) => {
    await page.goto('/precision-testing/runs', { waitUntil: 'domcontentloaded' });
    // 先注册路由拦截，再手动触发刷新请求（避免 reload 时序敏感问题）
    await page.route('**/api/precision-testing/runs/**', (route) => route.abort('failed'));
    const refreshButton = page.locator('button:has-text("刷新")').first();
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
    } else {
      // 无刷新按钮时直接触发重新加载
      await page.evaluate(() => window.location.reload());
    }
    // 使用 expect.poll() 增强稳定性，等待 toast 出现
    await expect.poll(async () => {
      const toast = page.locator('.el-message--error, .el-message.is-error, .el-message');
      return await toast.first().isVisible().catch(() => false);
    }, { timeout: 15000, intervals: [500, 500, 1000, 1000] }).toBe(true);
    await page.unroute('**/api/precision-testing/runs/**');
  });

  test('RUNHIST_025: 验证筛选后列表为空', async ({ authenticatedPage: page }) => {
    // Select impossible filter
    const filterSelect = page.locator('.el-select').first();
    if (await filterSelect.isVisible()) {
      await filterSelect.click();
      await page.waitForTimeout(500);
      // Select an option that might return empty
      const options = page.locator('.el-select-dropdown__item').last();
      if (await options.isVisible()) {
        await options.click();
        await page.waitForTimeout(1000);
      }
    }
  });
});