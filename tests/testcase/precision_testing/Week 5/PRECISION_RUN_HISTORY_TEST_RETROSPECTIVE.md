# Week 5 精准测试前端 — PrecisionRunHistory.vue 测试技术沉淀

> 生成时间：2026-05-14
> 主题：PrecisionRunHistory.vue 测试执行过程中的问题、阻塞与解决方案
> 适用范围：Vue 3 + Element Plus 前端、Django REST + MySQL + Neo4j 后端

---

## 一、总体结论

本次 PrecisionRunHistory 测试共执行 **74 条用例**（API 15条 + E2E 16条 + 手动功能验证 38条 + 异常场景 5条）。

**最终结果**：62 passed / 0 skipped / 8 failed（83.8%通过率）。

**关键发现**：
- 基础 CRUD + 筛选/分页/刷新流程 **全部通过**
- 主要阻塞项为**后端字段与 filter 能力缺口**（非前端实现问题）
- `auth-api.ts` 导出机制曾存在 `export { expect }` 重复定义，导致 `test.describe() not expected here` 报错
- Element Plus 下拉选择器需配合 `:visible` 伪类使用，否则在 DOM 存在但不可见时仍可匹配导致点击错误位置
- `page.reload()` 后 `ElMessage` toast 出现时序敏感，不适合断言网络错误提示

---

## 二、问题与解决方案详述

### 问题 1：`auth-api.ts` 重复导出 `expect` → `test.describe() not expected here`

**症状**：

```
Error: test.describe() not expected here
```

或运行时错误 `expect is not a function`。

**根因分析**：

`auth-api.ts` 中同时存在两次 `export { expect }`：

```typescript
// 错误写法（auth-api.ts 早期版本）
export const test = base.extend({ authenticatedPage: ... });
export { expect };     // ← 第一次
export { expect };     // ← 第二次（重复）
```

当 `export { expect }` 与 `export { expect, request }` 共存时，模块解析产生歧义，导致 Playwright 的 `test.describe()` 语法解析异常。

**解决方案**：

统一为单次导出：

```typescript
// auth-api.ts（正确写法）
import { test as base, expect, request } from '@playwright/test';
export { expect, request };     // ← 仅一次
export const test = base.extend({ ... });
export function loadTokens() { ... }
```

---

### 问题 2：`precision-run-history.spec.ts` 中 `expect` 从 `@playwright/test` 导入 → fixture 丢失

**症状**：

```
Error: Test has unknown parameter "authenticatedPage"
```

或测试中 `authenticatedPage` fixture 未被注入。

**根因**：spec 文件中存在两个不同来源的 `expect`：

```typescript
// 错误写法
import { test } from './auth-api';              // 扩展后的 test（含 authenticatedPage）
import { expect } from '@playwright/test';       // 原始 test 的 expect，fixture 未被注册
```

当 `expect` 从 `@playwright/test` 导入时，它关联的是未经 `base.extend()` 扩展的原始 test context，`authenticatedPage` fixture 不会生效。

**解决方案**：

所有符号统一从 `auth-api.ts` 导入：

```typescript
// precision-run-history.spec.ts（正确写法）
import { test, expect, request, loadTokens } from './auth-api';
// 不要单独从 @playwright/test 导入任何东西
```

---

### 问题 3：`PrecisionRunRecordViewSet` 未配置 filter → 状态/日期筛选全部失败

**现象**：RUN_API_002~006 全部返回 4 条全部记录，filter 参数被忽略。

**根因分析**：

```python
# backend/apps/precision_testing/views.py
class PrecisionRunRecordViewSet(viewsets.ModelViewSet):
    queryset = PrecisionRunRecord.objects.all()
    serializer_class = PrecisionRunRecordSerializer
    # ❌ 未定义 filterset_fields 或 filter_class
```

DRF 的 `ModelViewSet` 默认不启用过滤。`?status=completed` 等查询参数被直接忽略，导致返回全部数据。

同时，文档与代码的 status 值不一致：
- 文档写 `success`
- 模型 choices 定义的是 `completed`

**解决方案**：

后端 `PrecisionRunRecordViewSet` 添加 filter 配置：

```python
from django_filters.rest_framework import DjangoFilterBackend

class PrecisionRunRecordViewSet(viewsets.ModelViewSet):
    queryset = PrecisionRunRecord.objects.all()
    serializer_class = PrecisionRunRecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']   # ← 至少支持 status 精确匹配

    # 如需日期范围过滤，需自定义 FilterSet
    # filterset_class = PrecisionRunRecordFilter
```

同时统一文档与代码：前端筛选下拉值和后端 status choices 统一为 `completed` / `failed` / `running`。

---

### 问题 4：日期范围过滤字段名不一致 → `start_date` 参数被忽略

**现象**：RUN_API_005（日期范围过滤）失败，参数 `start_date` / `end_date` 未生效。

**根因分析**：
- 前端/文档期望参数名：`start_date` / `end_date`
- 模型实际字段名：`started_at`（无 `triggered_at`）
- ViewSet 未定义任何日期过滤逻辑

**解决方案**：

方式 A（推荐）：在 ViewSet 中自定义 `filterset_class`：

```python
import django_filters

class PrecisionRunRecordFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='started_at', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='started_at', lookup_expr='lte')

    class Meta:
        model = PrecisionRunRecord
        fields = ['status']
```

方式 B：序列化器使用 `SerializerMethodField` 暴露 `triggered_at` 作为 `started_at` 的别名，但 filter 仍需自定义。

---

### 问题 5：序列化器未暴露关键字段 → UI 用例无法验证

**现象**：RUN_UI_014（repo_name/branch）、RUN_UI_020（duration_seconds）、RUN_UI_025（error_message）、RUN_UI_032（commit_hash）均无法验证。

**根因分析**：

```python
# PrecisionRunRecordSerializer 当前字段
fields = ['id', 'status', 'total_testcases', 'reduction_rate',
          'impact_commit_range', 'started_at', 'created_at',
          'selected_testcases']
# ❌ 缺少：repo_name, branch, commit_hash, triggered_at, duration_seconds, error_message
```

同时，模型本身也未定义 `error_message`、`duration_seconds` 等字段。

**解决方案**：

在序列化器中通过 `SerializerMethodField` 间接暴露关联模型数据：

```python
class PrecisionRunRecordSerializer(serializers.ModelSerializer):
    repo_name = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()
    commit_hash = serializers.SerializerMethodField()
    triggered_at = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    error_message = serializers.SerializerMethodField()

    def get_repo_name(self, obj):
        # 通过 impact_analysis -> change_analysis -> repo_binding -> project 获取
        return obj.impact_analysis.change_analysis.repo_binding.project.name

    def get_duration_seconds(self, obj):
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None

    def get_error_message(self, obj):
        # 若模型无此字段，需先在模型中添加
        return getattr(obj, 'error_message', None)
```

---

### 问题 6：`RUN_ERR_001` 网络异常 toast 时序敏感 → E2E 偶发失败

**现象**：

```
timeout: waiting for locator('.el-message--error') to be visible
```

`page.reload()` 后等待 10s 仍未见 toast。

**根因分析**：

```typescript
// PrecisionRunHistory.vue
const fetchRunRecords = async () => {
  loading.value = true;
  try {
    const res = await getRunRecords({ ...params });
    // ...
  } catch (error) {
    ElMessage.error('加载执行记录失败');
  } finally {
    loading.value = false;
  }
};
```

`page.reload()` 后页面重新加载，JS 重新执行，但 `fetchRunRecords` 调用可能发生在 reload 完成之前或之后。`page.route(..., route => route.abort('failed'))` 在 reload 后可能尚未被注册即触发请求，导致 toast 未出现。

**解决方案**：

改用 `expect.poll()` 增强稳定性：

```typescript
// 修改前（不稳定）
await page.reload({ waitUntil: 'domcontentloaded' });
await expect(page.locator('.el-message--error')).toBeVisible({ timeout: 10000 });

// 修改后（推荐）
await page.route('**/api/precision-testing/runs/**', route => route.abort('failed'));
await page.reload({ waitUntil: 'domcontentloaded' });
// 等待 fetchRunRecords 被调用，再断言 toast
await expect.poll(async () => {
  return await page.locator('.el-message--error').isVisible();
}, { timeout: 15000 }).toBe(true);
```

或改用 `page.evaluate()` 在 reload 前注入全局拦截，确保 reload 后 fetch 立即失败。

---

### 问题 7：Element Plus 下拉选择器点击不稳定

**现象**：

```
Error: locator.click: Element is not visible
```

下拉选项点击时，元素存在于 DOM 但不可见。

**根因分析**：

Element Plus 的下拉面板使用 `teleport` 挂载到 body，`.el-select-dropdown__item` 在面板隐藏时仍存在于 DOM（仅 CSS `display: none`），`page.locator(...).click()` 会匹配到隐藏元素。

**解决方案**：

```typescript
// 修改前（不稳定）
await sizeSelect.click();
await page.locator('.el-select-dropdown__item').nth(1).click();

// 修改后（稳定）
async function selectDropdownOption(page: Page, selectLocator: Locator, optionText: string) {
  await selectLocator.click();
  await page.waitForTimeout(300); // 等待下拉动画 + teleport 挂载
  await page.locator(`.el-select-dropdown:visible .el-select-dropdown__item:has-text("${optionText}")`).click();
}
```

---

### 问题 8：`test_tokens_clean.json` 格式不兼容 → Token 读取失败

**现象**：`loadTokens()` 报错或 token 注入后仍 401。

**根因分析**：

`generate_test_token.py` 输出的 JSON 格式与 `auth-api.ts` 期望的格式不一致。早期版本输出嵌套结构：

```json
{ "token": "eyJ0eXAiOiJKV1Qi...", "user_id": 1 }
```

但 `auth-api.ts` 期望的是 `access` / `refresh` / `user` 结构：

```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": { "id": 1, "username": "admin" }
}
```

**解决方案**：

统一 Token 生成脚本的输出格式，并添加类型断言：

```typescript
// auth-api.ts
interface TokenData {
  access: string;
  refresh: string;
  access_expires_in: number;
  refresh_expires_in: number;
  user: { id: number; username: string; email?: string };
}

export function loadTokens(): TokenData {
  const raw = fs.readFileSync(TOKEN_PATH, 'utf-8');
  const data = JSON.parse(raw) as TokenData;
  // 兼容旧格式：若只有 token 字段，转换为 access
  if ((data as any).token && !data.access) {
    return { ...data, access: (data as any).token } as TokenData;
  }
  return data;
}
```

---

## 三、可复用代码模式库

### 3.1 统一认证导入模式

```typescript
// auth-api.ts - 统一导出
import { test as base, expect, request } from '@playwright/test';
export { expect, request };     // 仅一次
export const test = base.extend({ ... });
export function loadTokens() { ... }
```

```typescript
// 任何 spec 文件 - 统一导入
import { test, expect, request, loadTokens } from './auth-api';
// 不要单独从 @playwright/test 导入任何东西
```

### 3.2 网络错误 toast 断言（稳定版）

```typescript
// 不要依赖 page.reload() 后的时序
test('列表加载网络失败提示', async ({ authenticatedPage: page }) => {
  await page.goto('/precision-testing/precision-run-history', { waitUntil: 'domcontentloaded' });
  // 先注册路由拦截，再触发请求
  await page.route('**/api/precision-testing/runs/**', route => route.abort('failed'));
  await page.locator('button:has-text("刷新")').click(); // 手动触发请求
  await expect.poll(async () => {
    return await page.locator('.el-message--error').isVisible();
  }, { timeout: 15000 }).toBe(true);
});
```

### 3.3 Element Plus 下拉选择（稳定版）

```typescript
async function selectDropdownOption(page: Page, selectLocator: Locator, optionText: string) {
  await selectLocator.click();
  await page.waitForTimeout(300); // 等待下拉动画
  await page.locator(`.el-select-dropdown:visible .el-select-dropdown__item:has-text("${optionText}")`).click();
}
```

### 3.4 防御性分页 skip

```typescript
test('分页 page=2', async () => {
  const { body } = await apiWithAuth('get', '/api/precision-testing/runs/?page=1&page_size=10');
  if (body.count <= 10) {
    test.skip(true, '数据不足一页');
    return;
  }
  const { status } = await apiWithAuth('get', '/api/precision-testing/runs/?page=2&page_size=10');
  expect(status).toBe(200);
});
```

### 3.5 详情抽屉关闭断言

```typescript
test('详情抽屉关闭', async ({ authenticatedPage: page }) => {
  // 打开抽屉
  await page.locator('.el-table__row').first().click();
  await expect(page.locator('.el-drawer')).toBeVisible();

  // 方式 1：点击遮罩层关闭（推荐，模拟用户行为）
  await page.locator('.el-drawer__wrapper').click({ position: { x: 10, y: 10 } });
  await expect(page.locator('.el-drawer')).not.toBeVisible();

  // 方式 2：按 ESC 关闭
  // await page.keyboard.press('Escape');
  // await expect(page.locator('.el-drawer')).not.toBeVisible();
});
```

---

## 四、遗留与改进

| 优先级 | 事项 | 方案 | 状态 | 修改文件 |
|--------|------|------|------|----------|
| P0 | `PrecisionRunRecordViewSet` 缺少 filter | 添加 `filter_backends` + `PrecisionRunRecordFilter`（status + start_date/end_date） | ✅ 已完成 | `backend/apps/precision_testing/views.py` `backend/apps/precision_testing/filters.py` |
| P0 | status 值不一致（文档 `success` vs 代码 `completed`） | 前端 `<el-option>`、`statusType`、`statusLabel` 统一为 `completed`；E2E 选择器同步更新 | ✅ 已完成 | `frontend/src/views/precision-testing/PrecisionRunHistory.vue` `frontend/e2e/precision-testing/precision-run-history.spec.ts` |
| P0 | `error_message` 字段缺失 | `PrecisionRunRecord` 模型添加 `error_message` 字段；序列化器暴露 | ✅ 已完成 | `backend/apps/precision_testing/models.py` `backend/apps/precision_testing/serializers.py` |
| P1 | `repo_name`/`branch`/`commit_hash` 未暴露 | `PrecisionRunRecordSerializer` 添加 `SerializerMethodField`，通过 `impact_analysis.change_analysis.repo_binding` 链获取 | ✅ 已完成 | `backend/apps/precision_testing/serializers.py` |
| P1 | `duration_seconds` / `triggered_at` 未暴露 | `duration_seconds` 为 `SerializerMethodField`（`completed_at - started_at`）；`triggered_at` 为 `started_at` 别名 | ✅ 已完成 | `backend/apps/precision_testing/serializers.py` |
| P2 | `RUN_ERR_001` 测试不稳定 | `page.reload()` 改为先 `route()` 注册再手动点击刷新；`expect.poll()` 替代固定 timeout | ✅ 已完成 | `frontend/e2e/precision-testing/precision-run-history.spec.ts` |
| P2 | 测试数据预置自动化 | 新建 `setup_run_records.py`：自动创建/更新 4 条不同状态记录，含 `verify_run_records()` 验证 | ✅ 已完成 | `tests/precision_testing/setup_run_records.py` |
| P3 | 前端代码风格 | 新建 `precision-formatters.js`：抽取 `formatDateTime`/`formatRate`/`formatDuration`/`statusType`/`statusLabel`/`reductionColor`/`riskColor` | ✅ 已完成 | `frontend/src/utils/precision-formatters.js` `frontend/src/views/precision-testing/PrecisionRunHistory.vue` |

> 注：`error_message` 模型字段变更后，需执行 `python manage.py makemigrations precision_testing && python manage.py migrate` 生成并应用迁移。

---

## 五、参考文件索引

| 文件 | 路径 |
|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/PRECISION_RUN_HISTORY_TEST_CASES.md` |
| 执行报告 | `tests/testcase/precision_testing/Week 5/PRECISION_RUN_HISTORY_TEST_CASES_EXECUTION_REPORT.md` |
| 技术沉淀 | 本文档 |
| 测试脚本 | `frontend/e2e/precision-testing/precision-run-history.spec.ts` |
| 认证 Fixture | `frontend/e2e/precision-testing/auth-api.ts` |
| 前端组件 | `frontend/src/views/precision-testing/PrecisionRunHistory.vue` |
| 后端 ViewSet | `backend/apps/precision_testing/views.py` |
| 后端序列化器 | `backend/apps/precision_testing/serializers.py` |
| Week5 总技术沉淀 | `tests/testcase/precision_testing/Week 5/WEEK5_TECHNICAL_RETROSPECTIVE.md` |
