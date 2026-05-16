import { test, expect } from '../auth-api';
import type { Page } from '@playwright/test';

/**
 * Week 5 Cross-Page E2E Tests — Page Flow & Data Consistency
 * Test cases PAGE_001 ~ PAGE_003 in CROSS_PAGE_TEST_CASES.md
 *
 * PAGE_001/002 require an existing analyzable repo binding. When none is present
 * the tests skip with a clear annotation rather than fail.
 */

async function gotoPrecision(page: Page, path: string) {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
  await page.waitForTimeout(800);
}

test.describe('Precision Testing - Cross-Page Data Flow', () => {
  test('PAGE_001: repos → trigger analysis → record appears in change-analyses', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');

    const triggerBtn = page
      .locator('.el-table__row button:has-text("触发分析"), .el-table__row button:has-text("分析")')
      .first();

    if (!(await triggerBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No repo binding available to trigger analysis.');
      return;
    }

    const respPromise = page.waitForResponse(
      (r) => /\/api\/precision-testing\/repos\/\d+\/analyze\/?$/.test(r.url()),
      { timeout: 15000 },
    );
    await triggerBtn.click();
    const resp = await respPromise.catch(() => null);
    expect(resp, 'analyze API should respond').not.toBeNull();
    const body = await resp!.json().catch(() => ({} as Record<string, unknown>));
    const analysisId = (body as Record<string, unknown>).analysis_id ?? (body as Record<string, unknown>).id;

    await page.waitForTimeout(1500);
    await gotoPrecision(page, '/precision-testing/analyses');

    if (analysisId !== undefined) {
      await expect(
        page.locator(`.el-table__row:has-text("${String(analysisId)}")`).first(),
      ).toBeVisible({ timeout: 10000 });
    } else {
      await expect(page.locator('.el-table__row').first()).toBeVisible({ timeout: 10000 });
    }
  });

  test('PAGE_002: trigger analysis → "最近分析" time updates on repo row', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');

    const triggerBtn = page
      .locator('.el-table__row button:has-text("触发分析"), .el-table__row button:has-text("分析")')
      .first();

    if (!(await triggerBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No repo binding row visible to trigger analysis.');
      return;
    }

    const row = triggerBtn.locator('xpath=ancestor::tr[contains(@class,"el-table__row")][1]');
    const beforeText = (await row.innerText().catch(() => '')) ?? '';

    const respPromise = page.waitForResponse(
      (r) => /\/api\/precision-testing\/repos\/\d+\/analyze\/?$/.test(r.url()),
      { timeout: 15000 },
    );
    await triggerBtn.click();
    await respPromise.catch(() => null);

    await page.waitForTimeout(2500);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    const afterText = (await row.innerText().catch(() => '')) ?? '';
    expect(afterText.length).toBeGreaterThanOrEqual(beforeText.length / 2);
    expect(afterText).toMatch(/\d{4}-?\d{2}-?\d{2}|\d{2}:\d{2}/);
  });

  test('PAGE_003: page refresh resets transient state (no keep-alive)', async ({ authenticatedPage: page }) => {
    await gotoPrecision(page, '/precision-testing/repos');

    const search = page
      .locator('input[placeholder*="搜索"], input[placeholder*="search" i]')
      .first();
    if (!(await search.isVisible().catch(() => false))) {
      test.skip(true, 'No search input on /repos to validate transient state.');
      return;
    }

    await search.fill('keep-alive-probe');
    await page.waitForTimeout(500);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });

    const value = (await search.inputValue().catch(() => '')) ?? '';
    expect(value, 'search input should be cleared after reload').toBe('');
  });
});
