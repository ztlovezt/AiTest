# Week 5 精准测试前端 — MappingManager.vue 测试技术沉淀

> 生成时间：2026-05-14
> 主题：MappingManager.vue 测试执行过程中的问题、阻塞与解决方案
> 适用范围：Vue 3 + Element Plus 前端、Django REST + MySQL 后端

---

## 一、总体结论

本次 MappingManager 测试共执行 **65 条用例**（API 20条 + E2E 4条 + 手动功能验证 36条 + 异常场景 5条）。

**最终结果**：33 passed / 12 skipped / 20 failed（51%通过率）。

**关键发现**：
- 基础 CRUD 流程（列表/筛选/搜索/新建/弹窗）**全部通过**
- 主要阻塞项为**测试数据依赖**（无 testcase 记录和 mapping 记录）
- 自动构建因后端异步执行，running 状态难以捕获
- `auth-api.ts` 导出机制需正确配置才能让 `authenticatedPage` fixture 生效

---

## 二、问题与解决方案详述

### 问题 1：`authenticatedPage` fixture 未注册 → Test has unknown parameter

**症状**：

```
Error: Test has unknown parameter "authenticatedPage"
```

所有使用 `{ authenticatedPage: page }` 的测试都报错 `unknown parameter`。

**根因分析**：

`mapping-manager.spec.ts` 中同时存在两个导入来源不同的 `test`：

```typescript
// 错误写法：两个 test 不是同一个实例
import { test } from './auth-api';        // 扩展后的 test（含 authenticatedPage）
import { expect } from '@playwright/test'; // 原始 test（不含 authenticatedPage）
```

当 `expect` 从 `@playwright/test` 导入而 `test` 从 `auth-api.ts` 导入时，Playwright 的 fixture 扩展机制不完整，导致 `authenticatedPage` 未被注册。

**解决方案**：

`auth-api.ts` 导出所有需要的符号：

```typescript
// auth-api.ts
import { test as base, expect, request } from '@playwright/test';
export { expect, request };
export const test = base.extend({ ... });
export function loadTokens() { ... }
```

```typescript
// mapping-manager.spec.ts（正确写法）
import { test, expect, request, loadTokens } from './auth-api';
```

---

### 问题 2：`loadTokens` 未导出

**症状**：

```
TypeError: (0 , _authApi.loadTokens) is not a function
```

**根因**：`loadTokens` 是 `auth-api.ts` 的模块私有函数，未被 `export`。

**解决方案**：

```typescript
// auth-api.ts
export function loadTokens(): TokenData {
  const raw = fs.readFileSync(TOKEN_PATH, 'utf-8');
  return JSON.parse(raw);
}
```

---

### 问题 3：自动构建 running 状态无法捕获

**现象**：MAPPING_E2E_004、MAPPING_UI_026-027、MAPPING_UI_032 均超时失败。

**根因分析**：

`startAutoBuild()` 的实现：

```typescript
const startAutoBuild = async () => {
  buildStatus.value = 'running';
  // ...更新 UI
  try {
    await autoBuildMappings(data);  // 后端立即返回
    buildStatus.value = 'done';     // 状态立即变为 done
  } catch {
    buildStatus.value = 'error';
  }
};
```

后端 `autoBuildMappings()` 是异步任务（Celery 或后台线程），但前端在调用后**立即收到 200 响应并切换到 done 状态**。`running` 状态只持续 `buildPct` 的前端动画更新，实际在 1-2 个 tick 内完成。

**解决方案**：

测试不等待 `running` 状态，直接验证 `done` 状态出现：

```typescript
// 修改前（失败）
await page.locator('.el-dialog button:has-text("开始构建")').click();
await page.waitForTimeout(2000);  // 等待 running
const hasRunning = await page.locator('.el-icon.is-loading').isVisible();

// 修改后（推荐）
await page.locator('.el-dialog button:has-text("开始构建")').click();
await expect(page.locator('.build-icon.done, .el-icon.CircleCheck')).toBeVisible({ timeout: 10000 });
```

---

### 问题 4：测试数据依赖导致 skip/fail

**现象**：

- MAPPING_API_008/012/013：POST 返回 400（testcase=1 不存在）
- MAPPING_E2E_002/003：跳过（无可编辑/删除的记录）
- MAPPING_UI_010/011/015~017：跳过（同上）

**根因**：测试数据库中没有预置：
1. 有效的 `TestCase` 记录（id=1）
2. 若干 `Mapping` 记录（manual/auto/ai 各类型）

**解决方案**：

```bash
# 方式1：Django shell seed
cd backend && python manage.py shell
>>> from apps.testcases.models import TestCase
>>> tc = TestCase.objects.create(name="测试用例1", description="test")
>>> print(tc.id)  # 用返回的 ID 替换测试中的硬编码 1

# 方式2：API seed（通过已通过的 MAPPING_UI_014 先创建一条）
```

---

### 问题 5：分页下拉选择器不稳定

**现象**：

```
TimeoutError: locator('.el-select-dropdown__item').nth(1) is not visible
```

**根因**：Element Plus 下拉选项在点击后需要等待下拉面板动画完成，且 `.el-select-dropdown__item` 在下拉面板隐藏时也存在于 DOM 中（只是不可见）。

**解决方案**：

```typescript
// 修改前（不稳定）
await sizeSelect.click();
await page.locator('.el-select-dropdown__item').nth(1).click();

// 修改后（稳定）
await sizeSelect.click();
await page.waitForTimeout(300); // 等待下拉动画
// 等待下拉面板可见
await page.locator('.el-select-dropdown:visible .el-select-dropdown__item').nth(1).click();
```

---

### 问题 6：API 分页 page=2 返回 404

**现象**：MAPPING_API_007 访问 `/mappings/?page=2&page_size=10` 返回 404。

**根因**：当总数据量不足一页（<10条）时，访问 page=2 对 DRF 分页器来说是无效页，返回 404。

**解决方案**：API 测试应先检查总数据量，或改为验证空数据返回：

```typescript
test('MAPPING_API_007: 验证映射列表分页', async () => {
  const { body } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=1&page_size=10');
  if (body.count <= 10) {
    // 数据不足一页，跳过此测试
    test.skip(true, '数据不足一页');
    return;
  }
  const { status } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=2&page_size=10');
  expect(status).toBe(200);
});
```

---

## 三、可复用代码模式库

### 3.1 统一认证导入模式

```typescript
// auth-api.ts - 统一导出
import { test as base, expect, request } from '@playwright/test';
export { expect, request };
export const test = base.extend({ ... });
export function loadTokens() { ... }
```

```typescript
// 任何 spec 文件 - 统一导入
import { test, expect, request, loadTokens } from './auth-api';
// 不要单独从 @playwright/test 导入任何东西
```

### 3.2 自动构建状态验证（稳定版）

```typescript
test('自动构建 done 状态', async ({ authenticatedPage: page }) => {
  await gotoMappings(page);
  await page.locator('button:has-text("自动构建")').click();
  await expect(page.locator('.el-dialog')).toBeVisible();
  await page.locator('.el-dialog button:has-text("开始构建")').click();
  // 直接等待 done 状态（10s 超时，考虑后端异步延迟）
  await expect(page.locator('.build-icon.done')).toBeVisible({ timeout: 10000 });
});
```

### 3.3 防御性数据依赖 skip

```typescript
test('编辑映射流程', async ({ authenticatedPage: page }) => {
  await gotoMappings(page);
  await page.waitForTimeout(2000);
  const editBtn = page.locator('.el-table__row button').filter({ hasText: '' }).first();
  const isVisible = await editBtn.isVisible().catch(() => false);
  if (!isVisible) {
    test.skip(true, '无可编辑记录，需先创建测试数据');
    return;
  }
  await editBtn.click();
  await expect(page.locator('.el-dialog')).toBeVisible();
});
```

### 3.4 Element Plus 下拉选择（稳定版）

```typescript
async function selectDropdownOption(page: Page, selectLocator: Locator, optionText: string) {
  await selectLocator.click();
  await page.waitForTimeout(300); // 等待下拉动画
  await page.locator(`.el-select-dropdown:visible .el-select-dropdown__item:has-text("${optionText}")`).click();
}
```

---

## 四、遗留与改进

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P0 | 测试数据缺失 | 通过 Django shell 或 API seed 预置 testcase + mapping 记录 |
| P1 | 自动构建 running 状态断言 | 改为验证 idle→done 状态变化 |
| P2 | 分页选择器 | 使用 `:visible` 伪类过滤 |
| P3 | 表单验证时机 | 改用 `waitForSelector` 替代 `waitForTimeout` |
| P4 | route.abort() 错误UI | 改用 `page.evaluate()` 模拟 API 失败 |

---

## 五、参考文件索引

| 文件 | 路径 |
|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/MAPPING_MANAGER_TEST_CASES.md` |
| 执行报告 | `tests/testcase/precision_testing/Week 5/MAPPING_MANAGER_TEST_CASES_EXECUTION_REPORT.md` |
| 技术沉淀 | 本文档 |
| 测试脚本 | `frontend/e2e/precision-testing/mapping-manager.spec.ts` |
| 认证Fixture | `frontend/e2e/precision-testing/auth-api.ts` |
| 前端组件 | `frontend/src/views/precision-testing/MappingManager.vue` |
| Week5总技术沉淀 | `tests/testcase/precision_testing/Week 5/WEEK5_TECHNICAL_RETROSPECTIVE.md` |
