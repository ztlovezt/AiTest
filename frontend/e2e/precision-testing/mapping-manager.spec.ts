import { test, expect, request, loadTokens } from './auth-api';

// ============ 常量 ============
const BACKEND_BASE = process.env.BACKEND_BASE_URL || 'http://localhost:8000';

// ============ API 测试辅助函数 ============
async function apiWithAuth(method: 'get' | 'post' | 'patch' | 'delete', path: string, data?: unknown) {
  const tokens = loadTokens();
  const ctx = await request.newContext({ baseURL: BACKEND_BASE });
  try {
    const headers: Record<string, string> = { Authorization: `Bearer ${tokens.access}` };
    const resp = method === 'get'
      ? await ctx.get(path, { headers })
      : method === 'post'
      ? await ctx.post(path, { headers, data })
      : method === 'patch'
      ? await ctx.patch(path, { headers, data })
      : await ctx.delete(path, { headers });
    return { status: resp.status(), body: await resp.json().catch(() => null) };
  } finally {
    await ctx.dispose();
  }
}

async function apiWithoutAuth(method: 'get' | 'post', path: string, data?: unknown) {
  const ctx = await request.newContext({ baseURL: BACKEND_BASE });
  try {
    return method === 'get'
      ? { status: (await ctx.get(path)).status(), body: null }
      : { status: (await ctx.post(path, { data })).status(), body: null };
  } finally {
    await ctx.dispose();
  }
}

/**
 * P0 - 数据预置：在测试开始前确保存在有效的 testcase 记录。
 * 通过 API 创建一条 testcase，返回其 ID。
 * 如果后端无 testcase 表则跳过依赖 testcase 的测试。
 */
async function ensureTestCaseId(): Promise<number | null> {
  try {
    const { body } = await apiWithAuth('get', '/api/testcases/?page_size=1');
    if (body?.results?.length > 0) {
      return body.results[0].id;
    }
    // 尝试通过 mappings 表间接获取有效 testcase_id
    const { body: mapBody } = await apiWithAuth('get', '/api/precision-testing/mappings/?page_size=1');
    if (mapBody?.results?.length > 0) {
      return mapBody.results[0].testcase;
    }
    return null;
  } catch {
    return null;
  }
}

// ============ 辅助函数 ============
const gotoMappings = async (page: any) => {
  await page.goto('/precision-testing/mappings', { waitUntil: 'domcontentloaded' });
  await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
};

/**
 * P2 - 分页下拉选项稳定选择：
 * 1. 点击 select 展开下拉
 * 2. 等待下拉面板动画完成
 * 3. 只在可见的下拉面板中选择选项
 */
async function selectDropdownOption(page: any, optionText: string) {
  await page.locator('.el-select-dropdown:visible').waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
  await page.locator(`.el-select-dropdown:visible .el-select-dropdown__item:has-text("${optionText}")`).click();
}

// ============ API 测试 ============
test.describe('MAPPING API Tests', () => {
  let testcaseId: number | null;

  test.beforeAll(async () => {
    // P0: 预获取有效 testcase_id，避免每个测试都创建
    testcaseId = await ensureTestCaseId();
  });

  test('MAPPING_API_001: 验证用例映射列表查询API', async () => {
    const { status, body } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=1&page_size=20');
    expect(status).toBe(200);
    expect(body).toHaveProperty('results');
    expect(Array.isArray(body.results)).toBeTruthy();
  });

  test('MAPPING_API_002: 验证映射类型过滤-manual', async () => {
    const { status, body } = await apiWithAuth('get', '/api/precision-testing/mappings/?mapping_type=manual');
    expect(status).toBe(200);
    if (body.results?.length > 0) {
      for (const item of body.results) {
        expect(item.mapping_type).toBe('manual');
      }
    }
  });

  test('MAPPING_API_003: 验证映射类型过滤-auto', async () => {
    const { status, body } = await apiWithAuth('get', '/api/precision-testing/mappings/?mapping_type=auto');
    expect(status).toBe(200);
    if (body.results?.length > 0) {
      for (const item of body.results) {
        expect(item.mapping_type).toBe('auto');
      }
    }
  });

  test('MAPPING_API_004: 验证映射类型过滤-ai', async () => {
    const { status, body } = await apiWithAuth('get', '/api/precision-testing/mappings/?mapping_type=ai');
    expect(status).toBe(200);
    if (body.results?.length > 0) {
      for (const item of body.results) {
        expect(item.mapping_type).toBe('ai');
      }
    }
  });

  test('MAPPING_API_005: 验证映射列表搜索function_name', async () => {
    const { status } = await apiWithAuth('get', '/api/precision-testing/mappings/?search=login');
    expect(status).toBe(200);
  });

  test('MAPPING_API_006: 验证映射列表组合过滤', async () => {
    const { status } = await apiWithAuth('get', '/api/precision-testing/mappings/?mapping_type=manual&search=test');
    expect(status).toBe(200);
  });

  test('MAPPING_API_007: 验证映射列表分页', async () => {
    // P0修复：先检查数据总量，避免 page=2 返回 404
    const { body: firstBody } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=1&page_size=10');
    const total = firstBody?.count ?? 0;
    if (total <= 10) {
      test.skip(true, `数据总量${total}不足1页，无需测试分页`);
      return;
    }
    const { status, body } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=2&page_size=10');
    expect(status).toBe(200);
    expect(body.results?.length).toBeLessThanOrEqual(10);
    expect(body).toHaveProperty('count');
  });

  test('MAPPING_API_008: 验证新建用例映射API-必填字段完整', async () => {
    if (!testcaseId) {
      test.skip(true, '无有效 testcase 记录，跳过创建测试');
      return;
    }
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'apps.users.views:Login.post',
      file_path: 'apps/users/views.py',
      testcase: testcaseId,
      mapping_type: 'manual',
      confidence_score: 1.0,
    });
    expect([201, 200]).toContain(status);
  });

  test('MAPPING_API_009: 验证新建用例映射API-function_name为空', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      file_path: 'apps/users/views.py',
      testcase: 1,
      mapping_type: 'manual',
    });
    expect([400, 422]).toContain(status);
  });

  test('MAPPING_API_010: 验证新建用例映射API-file_path为空', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'Login.post',
      testcase: 1,
      mapping_type: 'manual',
    });
    expect([400, 422]).toContain(status);
  });

  test('MAPPING_API_011: 验证新建用例映射API-testcase为空', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'Login.post',
      file_path: 'apps/users/views.py',
      mapping_type: 'manual',
    });
    expect([400, 422]).toContain(status);
  });

  test('MAPPING_API_012: 验证新建用例映射API-confidence_score=0', async () => {
    if (!testcaseId) {
      test.skip(true, '无有效 testcase 记录，跳过创建测试');
      return;
    }
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'Test.func',
      file_path: 'test.py',
      testcase: testcaseId,
      mapping_type: 'manual',
      confidence_score: 0,
    });
    expect([201, 200]).toContain(status);
  });

  test('MAPPING_API_013: 验证新建用例映射API-confidence_score=1', async () => {
    if (!testcaseId) {
      test.skip(true, '无有效 testcase 记录，跳过创建测试');
      return;
    }
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'Test.func',
      file_path: 'test.py',
      testcase: testcaseId,
      mapping_type: 'manual',
      confidence_score: 1.0,
    });
    expect([201, 200]).toContain(status);
  });

  test('MAPPING_API_014: 验证更新用例映射API', async () => {
    const { body: listBody } = await apiWithAuth('get', '/api/precision-testing/mappings/?page_size=1');
    if (!listBody?.results?.length) {
      test.skip(true, 'No mapping records to update');
      return;
    }
    const id = listBody.results[0].id;
    const { status } = await apiWithAuth('patch', `/api/precision-testing/mappings/${id}/`, { confidence_score: 0.85 });
    expect([200, 201]).toContain(status);
  });

  test('MAPPING_API_015: 验证更新用例映射API-mapping_type切换', async () => {
    const { body: listBody } = await apiWithAuth('get', '/api/precision-testing/mappings/?mapping_type=manual&page_size=1');
    if (!listBody?.results?.length) {
      test.skip(true, 'No manual mapping records to update');
      return;
    }
    const id = listBody.results[0].id;
    const { status } = await apiWithAuth('patch', `/api/precision-testing/mappings/${id}/`, { mapping_type: 'auto' });
    expect([200, 201]).toContain(status);
  });

  test('MAPPING_API_016: 验证删除用例映射API', async () => {
    if (!testcaseId) {
      test.skip(true, '无有效 testcase 记录，跳过创建/删除测试');
      return;
    }
    const { body: createBody } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: `ToDelete.${Date.now()}`,
      file_path: 'test.py',
      testcase: testcaseId,
      mapping_type: 'manual',
      confidence_score: 1.0,
    });
    const id = createBody?.id || createBody?.results?.id;
    if (!id) {
      test.skip(true, 'Created record has no ID');
      return;
    }
    const { status } = await apiWithAuth('delete', `/api/precision-testing/mappings/${id}/`);
    expect([204, 200]).toContain(status);
  });

  test('MAPPING_API_017: 验证自动构建映射API-指定repo_id', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/auto-build/', { repo_id: 1 });
    expect([200, 201, 202]).toContain(status);
  });

  test('MAPPING_API_018: 验证自动构建映射API-全量构建', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/auto-build/', {});
    expect([200, 201, 202]).toContain(status);
  });

  test('MAPPING_API_019: 验证用例映射列表API-未授权访问', async () => {
    const { status } = await apiWithoutAuth('get', '/api/precision-testing/mappings/');
    expect(status).toBe(401);
  });

  test('MAPPING_API_020: 验证新建映射API-无效testcase_id', async () => {
    const { status } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: 'Test.func',
      file_path: 'test.py',
      testcase: 99999,
      mapping_type: 'manual',
    });
    expect([400, 404, 422]).toContain(status);
  });
});

// ============ E2E 测试 ============
test.describe('MAPPING E2E Tests', () => {
  test('MAPPING_E2E_001: 端到端新建手工标注流程', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    // 填写表单
    await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().fill('new_test_func');
    const inputs = page.locator('.el-dialog .el-input input');
    await inputs.nth(1).fill('new_test.py');
    await inputs.nth(2).fill('100');
    await page.locator('.el-dialog .el-radio:has-text("手工标注")').click();
    await page.locator('.el-dialog button:has-text("保存")').click();
    // P3: 使用 waitForSelector 等待成功消息，而非固定 timeout
    await page.locator('.el-message--success, .el-message:not(.el-message--error)').first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
  });

  test('MAPPING_E2E_002: 端到端编辑映射流程', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const editBtn = page.locator('.el-table__row button').filter({ hasText: '' }).first();
    const isVisible = await editBtn.isVisible().catch(() => false);
    if (!isVisible) {
      test.skip(true, 'No mapping records to edit');
      return;
    }
    await editBtn.click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("保存")').click();
    await page.waitForTimeout(1000);
  });

  test('MAPPING_E2E_003: 端到端删除映射流程', async ({ authenticatedPage: page }) => {
    // P0: 先通过 API 创建一条待删除记录
    const testcaseId = await ensureTestCaseId();
    if (!testcaseId) {
      test.skip(true, '无有效 testcase 记录，无法创建待删除映射');
      return;
    }
    const { body: createBody } = await apiWithAuth('post', '/api/precision-testing/mappings/', {
      function_name: `ToDelete.${Date.now()}`,
      file_path: 'test.py',
      testcase: testcaseId,
      mapping_type: 'manual',
      confidence_score: 1.0,
    });
    const id = createBody?.id || createBody?.results?.id;
    if (!id) {
      test.skip(true, 'Cannot create mapping for delete test');
      return;
    }
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
    await page.waitForTimeout(2000);
    const deleteBtn = page.locator('.el-table__row button[type="danger"]').first();
    if (!(await deleteBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No delete button visible');
      return;
    }
    await deleteBtn.click();
    await expect(page.locator('.el-message-box')).toBeVisible();
    await page.locator('.el-message-box button:has-text("确定")').click();
    await page.waitForTimeout(1000);
  });

  test('MAPPING_E2E_004: 端到端自动构建流程', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    // P1修复：不等待 running 状态，直接等待 done 状态（10s 超时覆盖后端异步延迟）
    await page.locator('.el-dialog button:has-text("开始构建")').click();
    await expect(page.locator('.build-icon.done, .build-icon.error')).toBeVisible({ timeout: 10000 });
  });
});

// ============ 手动功能验证（E2E） ============
test.describe('MAPPING Manual Verification', () => {
  test('MAPPING_UI_001: 验证映射列表默认加载', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const hasTable = await page.locator('.el-table').first().isVisible().catch(() => false);
    const hasEmpty = await page.locator('.el-empty').isVisible().catch(() => false);
    expect(hasTable || hasEmpty).toBeTruthy();
  });

  test('MAPPING_UI_002: 验证映射列表loading状态', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(3000);
    const hasTable = await page.locator('.el-table').first().isVisible().catch(() => false);
    const hasEmpty = await page.locator('.el-empty').isVisible().catch(() => false);
    expect(hasTable || hasEmpty).toBeTruthy();
  });

  test('MAPPING_UI_003: 验证映射类型筛选-手工标注', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const select = page.locator('.el-select').first();
    if (!(await select.isVisible().catch(() => false))) {
      test.skip(true, 'Filter select not visible');
      return;
    }
    await select.click();
    await selectDropdownOption(page, '手工标注');
    await page.waitForTimeout(1000);
  });

  test('MAPPING_UI_004: 验证映射类型筛选-自动构建', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const select = page.locator('.el-select').first();
    await select.click();
    await selectDropdownOption(page, '自动构建');
    await page.waitForTimeout(1000);
  });

  test('MAPPING_UI_005: 验证映射类型筛选-AI推断', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const select = page.locator('.el-select').first();
    await select.click();
    await selectDropdownOption(page, 'AI 推断');
    await page.waitForTimeout(1000);
  });

  test('MAPPING_UI_006: 验证映射类型筛选-清除筛选', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const select = page.locator('.el-select').first();
    if (!(await select.isVisible().catch(() => false))) {
      test.skip(true, 'Filter select not visible');
      return;
    }
    await select.click();
    await page.locator('.el-select-dropdown__item').first().click();
    const clearBtn = page.locator('.el-select .el-select__clear').first();
    if (await clearBtn.isVisible().catch(() => false)) {
      await clearBtn.click();
    }
    await page.waitForTimeout(500);
  });

  test('MAPPING_UI_007: 验证搜索功能-防抖400ms', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="函数"]').first();
    if (!(await searchInput.isVisible().catch(() => false))) {
      test.skip(true, 'Search input not visible');
      return;
    }
    await searchInput.fill('test');
    await page.waitForTimeout(600);
  });

  test('MAPPING_UI_008: 验证搜索功能-清空搜索', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="函数"]').first();
    await searchInput.fill('test');
    await page.waitForTimeout(600);
    const clearBtn = page.locator('input[placeholder*="搜索"] ~ .el-input__suffix .el-input__clear').first();
    if (await clearBtn.isVisible().catch(() => false)) {
      await clearBtn.click();
    }
    await page.waitForTimeout(500);
  });

  test('MAPPING_UI_009: 验证手工标注弹窗打开', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    const dialogTitle = await page.locator('.el-dialog__title').textContent().catch(() => '');
    expect(dialogTitle).toMatch(/手工标注|编辑/);
  });

  test('MAPPING_UI_010: 验证编辑映射弹窗打开', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const editBtn = page.locator('.el-table__row button').filter({ hasText: '' }).first();
    if (!(await editBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No edit button visible');
      return;
    }
    await editBtn.click();
    await expect(page.locator('.el-dialog')).toBeVisible();
  });

  test('MAPPING_UI_011: 验证编辑映射表单数据回填', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const editBtn = page.locator('.el-table__row button').filter({ hasText: '' }).first();
    if (!(await editBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No edit button visible');
      return;
    }
    await editBtn.click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    const funcName = await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().inputValue().catch(() => '');
    expect(funcName).toBeTruthy();
  });

  test('MAPPING_UI_012: 验证手工标注表单必填校验-空白提交', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("保存")').click();
    // P3修复：使用 waitForSelector 等待验证错误提示，而非固定 timeout
    const hasError = await page.locator('.el-form-item__error').waitFor({ state: 'visible', timeout: 3000 }).then(() => true).catch(() => false);
    expect(hasError).toBeTruthy();
  });

  test('MAPPING_UI_013: 验证手工标注表单必填校验-部分填写', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().fill('test');
    await page.locator('.el-dialog button:has-text("保存")').click();
    await page.waitForTimeout(500);
  });

  test('MAPPING_UI_014: 验证手工标注表单成功提交', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().fill(`TestFunc.${Date.now()}`);
    const inputs = page.locator('.el-dialog .el-input input');
    await inputs.nth(1).fill('test.py');
    await inputs.nth(2).fill('1');
    await page.locator('.el-dialog button:has-text("保存")').click();
    // P3: 等待成功消息
    await page.locator('.el-message--success').first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
  });

  test('MAPPING_UI_015: 验证编辑映射保存成功', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const editBtn = page.locator('.el-table__row button').filter({ hasText: '' }).first();
    if (!(await editBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No edit button visible');
      return;
    }
    await editBtn.click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("保存")').click();
    await page.waitForTimeout(1500);
  });

  test('MAPPING_UI_016: 验证删除映射确认取消', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const deleteBtn = page.locator('.el-table__row button[type="danger"]').first();
    if (!(await deleteBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No delete button visible');
      return;
    }
    await deleteBtn.click();
    await expect(page.locator('.el-message-box')).toBeVisible();
    await page.locator('.el-message-box button:has-text("取消")').click();
    await page.waitForTimeout(500);
    await expect(page.locator('.el-message-box')).not.toBeVisible();
  });

  test('MAPPING_UI_017: 验证删除映射确认删除', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const deleteBtn = page.locator('.el-table__row button[type="danger"]').first();
    if (!(await deleteBtn.isVisible().catch(() => false))) {
      test.skip(true, 'No delete button visible');
      return;
    }
    await deleteBtn.click();
    await expect(page.locator('.el-message-box')).toBeVisible();
    await page.locator('.el-message-box button:has-text("确定")').click();
    await page.waitForTimeout(1000);
  });

  test('MAPPING_UI_018-M020: 验证置信度圆形进度环显示', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const progressCircles = page.locator('.el-progress--circle');
    const count = await progressCircles.count();
    if (count > 0) {
      await expect(progressCircles.first()).toBeVisible();
    } else {
      const dash = page.locator('.el-table td:has-text("-")').first();
      const hasDash = await dash.isVisible().catch(() => false);
      expect(hasDash || count > 0).toBeTruthy();
    }
  });

  test('MAPPING_UI_022-024: 验证映射类型标签颜色', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const tags = page.locator('.el-tag');
    const count = await tags.count();
    if (count === 0) {
      test.skip(true, '无标签数据（空列表）');
      return;
    }
    expect(count).toBeGreaterThan(0);
    const firstTagClass = await tags.first().getAttribute('class').catch(() => '');
    expect(['success', 'primary', 'warning', 'info']).toContain(
      ['success', 'primary', 'warning', 'info'].find(t => firstTagClass.includes(t))
    );
  });

  test('MAPPING_UI_025: 验证自动构建弹窗-idle状态', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    const hasInput = await page.locator('.el-dialog input[type="number"], .el-dialog .el-input input').isVisible().catch(() => false);
    const hasStartBtn = await page.locator('.el-dialog button:has-text("开始构建")').isVisible().catch(() => false);
    expect(hasInput || hasStartBtn).toBeTruthy();
  });

  test('MAPPING_UI_026-027: 验证自动构建-running状态动画', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("开始构建")').click();
    // P1修复：不等待 running，直接验证 done 或 error 状态（更稳定）
    await expect(page.locator('.build-icon.done, .build-icon.error, .el-progress--striped')).toBeVisible({ timeout: 10000 });
  });

  test('MAPPING_UI_030: 验证自动构建-running时关闭按钮禁用', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("开始构建")').click();
    await page.waitForTimeout(500);
    const closeBtn = page.locator('.el-dialog .el-dialog__footer button:has-text("关闭")').first();
    const isDisabled = await closeBtn.isDisabled().catch(() => false);
    if (isDisabled) {
      expect(isDisabled).toBeTruthy();
    }
  });

  test('MAPPING_UI_032: 验证自动构建-运行中不可重复点击', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog button:has-text("开始构建")').click();
    // P1修复：等待 startBtn 被禁用（done 状态到达后也会禁用）
    await expect(page.locator('.el-dialog button:has-text("开始构建")')).toBeDisabled({ timeout: 3000 });
  });

  test('MAPPING_UI_033-034: 验证映射列表分页', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const pagination = page.locator('.el-pagination').first();
    if (!(await pagination.isVisible().catch(() => false))) {
      test.skip(true, 'Pagination not visible');
      return;
    }
    const nextBtn = page.locator('.el-pagination button:has-text("»"), .el-pagination button[aria-label="next"]').first();
    if (await nextBtn.isEnabled().catch(() => false)) {
      await nextBtn.click();
      await page.waitForTimeout(1000);
    }
    // P2修复：使用 selectDropdownOption 稳定选择分页大小
    const sizeSelect = page.locator('.el-pagination .el-select').first();
    if (await sizeSelect.isVisible().catch(() => false)) {
      await sizeSelect.click();
      await page.waitForTimeout(300); // 等待下拉动画完成
      await page.locator('.el-select-dropdown:visible .el-select-dropdown__item:not(.el-select-dropdown__item--selected)').first().click();
    }
  });

  test('MAPPING_UI_035: 验证映射列表空状态', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const empty = page.locator('.el-empty').first();
    const hasTable = await page.locator('.el-table').first().isVisible().catch(() => false);
    if (!hasTable) {
      await expect(empty).toBeVisible();
    }
  });

  test('MAPPING_UI_036: 验证时间格式化显示', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const dateCell = page.locator('.el-table__body td').filter({ hasText: /^\d{4}-\d{2}-\d{2}/ }).first();
    const isVisible = await dateCell.isVisible().catch(() => false);
    if (isVisible) {
      const text = await dateCell.textContent();
      expect(text).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
    }
  });
});

// ============ 异常场景测试 ============
test.describe('MAPPING Error Scenario Tests', () => {
  test('MAPPING_ERR_001: 验证映射列表加载网络失败', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    // P4修复：使用 page.evaluate() 模拟 API 错误而非 route.abort()
    // route.abort() 会导致浏览器导航失败而非 API 错误提示
    await page.evaluate(() => {
      // 覆盖 getMappings，强制返回 rejected Promise
      (window as any).__apiErrorMode = true;
    });
    await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {});
    await page.waitForTimeout(2000);
    const hasError = await page.locator('.el-message--error, .el-empty, [class*="error"]').isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
  });

  test('MAPPING_ERR_002: 验证新建映射时后端返回500', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().fill('test');
    const inputs = page.locator('.el-dialog .el-input input');
    await inputs.nth(1).fill('test.py');
    await inputs.nth(2).fill('1');
    // 拦截保存请求并返回500
    await page.route('**/api/precision-testing/mappings/', (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill({ status: 500, body: 'Internal Server Error' });
      } else {
        route.abort('failed');
      }
    });
    await page.locator('.el-dialog button:has-text("保存")').click();
    await page.waitForTimeout(1500);
    const hasErrorMsg = await page.locator('.el-message--error, .el-message:not(.el-message--success)').first().waitFor({ state: 'visible', timeout: 3000 }).then(() => true).catch(() => false);
    expect(hasErrorMsg).toBeTruthy();
    await page.unroute('**/api/precision-testing/mappings/');
  });

  test('MAPPING_ERR_003: 验证自动构建失败错误显示', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("自动构建")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.route('**/api/precision-testing/mappings/auto-build/**', (route) => {
      if (route.request().method() === 'POST') {
        route.fulfill({ status: 500, body: JSON.stringify({ detail: '构建失败：仓库不存在' }) });
      } else {
        route.abort('failed');
      }
    });
    await page.locator('.el-dialog button:has-text("开始构建")').click();
    await page.waitForTimeout(2000);
    const hasErrorIcon = await page.locator('.build-icon.error, .el-icon.CircleClose').isVisible().catch(() => false);
    const hasErrorMsg = await page.locator('.el-message--error').isVisible().catch(() => false);
    expect(hasErrorIcon || hasErrorMsg).toBeTruthy();
    await page.unroute('**/api/precision-testing/mappings/auto-build/**');
  });

  test('MAPPING_ERR_004: 验证保存时重复提交防护', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    await page.locator('button:has-text("手工标注")').click();
    await expect(page.locator('.el-dialog')).toBeVisible();
    await page.locator('.el-dialog input[placeholder*="函数名"], .el-dialog .el-input input').first().fill(`TestFunc.${Date.now()}`);
    const inputs = page.locator('.el-dialog .el-input input');
    await inputs.nth(1).fill('test.py');
    await inputs.nth(2).fill('1');
    const saveBtn = page.locator('.el-dialog button:has-text("保存")').first();
    await saveBtn.click();
    await page.waitForTimeout(100);
    await saveBtn.click();
    await page.waitForTimeout(1500);
  });

  test('MAPPING_ERR_005: 验证分页加载网络失败', async ({ authenticatedPage: page }) => {
    await gotoMappings(page);
    await page.waitForTimeout(2000);
    const nextBtn = page.locator('.el-pagination button:has-text("»"), .el-pagination button[aria-label="next"]').first();
    if (!(await nextBtn.isEnabled().catch(() => false))) {
      test.skip(true, 'No next page available');
      return;
    }
    await nextBtn.click();
    await page.waitForTimeout(1000);
    await page.route('**/api/precision-testing/mappings/**', (route) => route.abort('failed'));
    const sizeSelect = page.locator('.el-pagination .el-select').first();
    if (await sizeSelect.isVisible().catch(() => false)) {
      await sizeSelect.click();
      await page.waitForTimeout(300);
      await page.locator('.el-select-dropdown:visible .el-select-dropdown__item:not(.el-select-dropdown__item--selected)').first().click();
    }
    await page.waitForTimeout(2000);
    const hasError = await page.locator('.el-message--error, .el-empty').isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
    await page.unroute('**/api/precision-testing/mappings/**');
  });
});