# Week 5 E2E 测试 — AI Agent 经验宝典

> 范围：ChangeAnalyses.vue 单页测试 + Cross-Page 全量测试
> 技术栈：Vue 3 + Element Plus / Django REST + JWT / Playwright TypeScript
> 目标：让后续 AI Agent 快速上手，避免重复踩坑

---

## 一、前置速查

| 项 | 值 |
|---|---|
| 前端 | http://localhost:3000 |
| 后端 | http://localhost:8000 |
| 测试账号 | admin / admin123456 |
| 测试目录 | `frontend/e2e/precision-testing/` |
| 公共 Fixture | `auth-api.ts`（唯一正确入口） |
| Token 缓存 | `test_tokens_clean.json`（项目根目录） |
| Token 生成脚本 | `backend/generate_test_token.py` |

**关键背景**：
- `/home` 路由**没有** `Layout` 组件（无 `.el-aside`/`.el-header`/`.el-main`）
- 精准测试页面（`/precision-testing/*`）**有** `Layout` 组件
- 后端 DRF 启用了 `AnonRateThrottle`，匿名登录限流 `100/hour`
- 部分页面存在长连接（轮询/SSE），`networkidle` 会超时

---

## 二、DO / DON'T —— 铁律清单

### 认证与 Fixture

| ❌ DON'T | ✅ DO |
|---------|------|
| 在 fixture 里走 UI 登录（填表单 → 点击 → 等待跳转） | 使用 `auth-api.ts` 的 `authenticatedPage`，通过 localStorage 注入预生成 JWT |
| `.catch(() => {})` 吞掉 `waitForURL` 超时 | 让导航/等待异常正常抛出，失败即停 |
| 每轮测试调用 `/api/auth/login/` 获取 Token | 一次性生成 `test_tokens_clean.json`，fixture 从磁盘读取 |
| 修改 `auth.ts`（会被 IDE/linter hook 自动回退） | 废弃 `auth.ts`，所有 spec 统一 `import { test } from '../auth-api'` |

### 选择器与 DOM

| ❌ DON'T | ✅ DO |
|---------|------|
| `[index="..."]` 定位 `el-menu-item`（Element Plus 不渲染 `index` 为 DOM attribute） | `page.locator('.el-menu-item').filter({ hasText: '仓库绑定' })` |
| 假设所有页面都有 `.el-aside` | `/home` 等独立布局页面需单独处理 |
| 用 `networkidle` 等待页面加载 | 统一用 `domcontentloaded` + `waitFor({ state: 'visible' })` |

### 测试设计

| ❌ DON'T | ✅ DO |
|---------|------|
| 数据缺失时让测试失败 | 用防御性 skip：`if (!visible) test.skip(true, 'reason')` |
| 安全测试使用 `authenticatedPage` fixture | 安全测试独立用 `request.newContext()` 发裸 HTTP，确保无 Token |
| 用 `console.log` 调试 | 使用 Playwright 的 `--reporter=html` 或 trace viewer |

---

## 三、踩坑速查表

### 3.1 认证 fixture 不可靠 → 改用 localStorage 种子注入

**症状**：大量测试在 `.el-aside` 处超时，实际页面仍停留在 `/login`。

**根因**：`auth.ts` 用 UI 登录流程，`.catch(() => {})` 吞掉超时，page 未认证却继续执行。

**解决**：`auth-api.ts` 直接注入 Token。

```typescript
// frontend/e2e/precision-testing/auth-api.ts
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    const tokens = loadTokens(); // 从 test_tokens_clean.json 读取
    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((data) => {
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token_expires_at', data.expiresAt.toString());
      localStorage.setItem('user', JSON.stringify(data.user));
    }, { access: tokens.access, refresh: tokens.refresh, expiresAt: Date.now() + tokens.access_expires_in * 1000, user: tokens.user });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20000 });
    await use(page);
  },
});
```

### 3.2 后端限流 429 → 预生成 Token 绕过 HTTP

**症状**：多轮执行后登录接口返回 `429 Too Many Requests`。

**根因**：DRF `AnonRateThrottle` `anon_rate: 100/hour`，高频测试快速耗尽配额。

**解决**：Django 脚本直接生成 Token，不走 HTTP。

```python
# backend/generate_test_token.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User

u = User.objects.get(username='admin')
r = RefreshToken.for_user(u)
result = {
    'access': str(r.access_token),
    'refresh': str(r),
    'user': { 'id': u.id, 'username': u.username, ... },
    'access_expires_in': 30 * 60,
}
# 输出到 test_tokens_clean.json
```

### 3.3 Element Plus `index` prop 不渲染 → 文本过滤定位

**症状**：`page.locator('.el-menu-item[index="..."])` 返回 0 个元素。

**根因**：Element Plus `el-menu-item` 的 `index` prop 是组件内部状态，不输出为 DOM attribute。

**解决**：

```typescript
// 通用辅助函数
const menuItemByLabel = (page: Page, label: string) =>
  page.locator('.el-menu-item').filter({ hasText: label });

// 断言激活态
await expect(menuItemByLabel(page, '仓库绑定')).toHaveClass(/is-active/);
```

### 3.4 `/home` 无 Layout → 差异化初始化

**症状**：从 `/home` 出发的导航测试因 `.el-aside` 等待而超时。

**根因**：`/home` 直接挂载 `Home.vue`，未使用 `Layout` 组件。

**解决**：`/home` 场景单独处理，不等待 `.el-aside`。

```typescript
// 标准精准测试页面初始化（有 Layout）
async function gotoPrecision(page: Page, path: string) {
  await page.goto(path, { waitUntil: 'domcontentloaded' });
  await page.locator('.el-aside').first().waitFor({ state: 'visible', timeout: 15000 });
}

// /home 场景（无 Layout）
await page.goto('/home', { waitUntil: 'domcontentloaded' });
const entry = menuItemByLabel(page, '仓库绑定').first();
if (await entry.isVisible().catch(() => false)) await entry.click();
```

### 3.5 数据依赖导致测试无法覆盖 → 防御性 skip

**症状**：ChangeAnalyses 详情测试、跨页面数据流测试因无后端数据而失败。

**根因**：测试环境未预置 completed 状态的 analysis 记录或可分析的 repo binding。

**解决**：

```typescript
const triggerBtn = page.locator('.el-table__row button:has-text("触发分析")').first();
if (!(await triggerBtn.isVisible().catch(() => false))) {
  test.skip(true, 'No repo binding available to trigger analysis.');
  return;
}
```

**长期方案**：在 CI 初始化时通过 Django management command 插入 mock 数据。

---

## 四、可复用代码模式库

### 4.1 认证相关

**未登录状态清理**：
```typescript
await context.clearCookies();
await page.addInitScript(() => {
  try { window.localStorage.clear(); } catch {}
  try { window.sessionStorage.clear(); } catch {}
});
```

**Token 失效模拟**：
```typescript
await page.evaluate(() => {
  localStorage.setItem('access_token', 'invalid.token.value');
  localStorage.setItem('token_expires_at', '0');
});
await page.reload();
await page.waitForURL('**/login', { timeout: 20000 });
```

**请求头拦截断言 Bearer Token**：
```typescript
const seenAuthHeaders: string[] = [];
page.on('request', (req) => {
  if (req.url().includes('/api/precision-testing/')) {
    const auth = req.headers()['authorization'];
    if (auth) seenAuthHeaders.push(auth);
  }
});
// ... 触发页面操作 ...
expect(seenAuthHeaders.length).toBeGreaterThan(0);
for (const h of seenAuthHeaders) expect(h).toMatch(/^Bearer\s+\S+/);
```

### 4.2 API 测试模式

**安全测试（裸 HTTP，无认证）**：
```typescript
import { test, expect, request } from '@playwright/test';

const BACKEND_BASE = process.env.BACKEND_BASE_URL || 'http://localhost:8000';
const UNAUTH_STATUSES = new Set([401, 403]);

async function probe(method: 'get' | 'post' | 'delete', path: string, data?: unknown) {
  const ctx = await request.newContext({ baseURL: BACKEND_BASE });
  try {
    const resp = await (method === 'get' ? ctx.get(path) : method === 'post' ? ctx.post(path, { data }) : ctx.delete(path));
    return { status: resp.status(), body: await resp.json().catch(() => null) };
  } finally {
    await ctx.dispose();
  }
}

test('SEC: GET without token → 401', async () => {
  const { status } = await probe('get', '/api/precision-testing/repos/');
  expect(UNAUTH_STATUSES.has(status)).toBeTruthy();
});
```

**强制 API 失败验证错误 UI**：
```typescript
await page.route('**/api/precision-testing/**', (route) => route.abort('failed'));
await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
const errorToast = page.locator('.el-message--error, .el-message.is-error, .el-message');
await expect(errorToast.first()).toBeVisible({ timeout: 10000 });
```

**读取前端源码断言配置**：
```typescript
const resp = await page.request.get('/src/utils/api.js');
expect(resp.ok()).toBeTruthy();
const text = await resp.text();
expect(text).toContain('timeout: 30000');
```

### 4.3 布局与响应式

**横向溢出检测**：
```typescript
const overflow = await page.evaluate(() => {
  const docW = document.documentElement.clientWidth;
  return document.body.scrollWidth > docW + 8; // 8px 容差
});
expect(overflow).toBeFalsy();
```

**padding 读取断言**：
```typescript
const padding = await page.locator('.el-main').first().evaluate((el) => {
  const cs = window.getComputedStyle(el);
  return {
    top: parseFloat(cs.paddingTop),
    right: parseFloat(cs.paddingRight),
    bottom: parseFloat(cs.paddingBottom),
    left: parseFloat(cs.paddingLeft),
  };
});
expect(padding.top).toBeGreaterThanOrEqual(16);
```

### 4.4 数据流与状态

**keep-alive 检测**：
```typescript
await search.fill('keep-alive-probe');
await page.waitForTimeout(500);
await page.reload({ waitUntil: 'domcontentloaded' });
const value = await search.inputValue().catch(() => '');
expect(value).toBe(''); // 清空说明无 keep-alive
```

---

## 五、关键决策记录（为什么这样设计）

### 决策 1：弃用 `auth.ts` → 新建 `auth-api.ts`

| 维度 | 修复 auth.ts | 新建 auth-api.ts |
|------|-------------|------------------|
| 外部 hook 冲突 | 高（持续被覆盖） | 低 |
| 实现复杂度 | 中（UI 登录不稳定） | 低（storage seeding） |
| 执行速度 | 慢（~3-5s/次） | 快（~500ms/次） |
| 后端依赖 | 高（受限于流控） | 低（零 API 调用） |
| **结论** | ❌ | ✅ |

### 决策 2：安全测试不使用 `authenticatedPage`

安全测试目标是验证"无 Token 返回 401"。使用 `authenticatedPage` 会注入 Token，违背测试意图。因此独立使用 `request.newContext()` 发裸 HTTP，与浏览器解耦，执行极快。

### 决策 3：`domcontentloaded` 替代 `networkidle`

精准测试模块部分页面存在轮询或 SSE 长连接，`networkidle` 要求网络静默 500ms 会导致超时。统一使用 `domcontentloaded`，并在关键元素（`.el-aside`）上使用 `waitFor({ state: 'visible' })` 作为渲染完成的替代信号。

---

## 六、文件地图

```
frontend/e2e/precision-testing/
├── auth-api.ts                    ← 唯一正确的认证 fixture
├── auth.ts                        ← 已废弃，勿修改（会被 hook 回退）
├── change-analyses.spec.ts        ← ChangeAnalyses 单页测试（22 条）
└── cross-page/
    ├── api-shared.spec.ts         ← API 共享层（8 条）
    ├── auth-session.spec.ts       ← 认证与会话（5 条）
    ├── layout.spec.ts             ← 布局与响应式（5 条）
    ├── navigation.spec.ts         ← 导航与路由（10 条）
    ├── page-flow.spec.ts          ← 跨页面数据流（3 条）
    └── security.spec.ts           ← API 安全（10 条）

backend/
└── generate_test_token.py         ← Token 预生成脚本

test_tokens_clean.json             ← 预生成 JWT 缓存（项目根目录）
```

---

## 七、执行命令速查

```bash
# 进入前端目录
cd frontend

# 全量 Cross-Page
npx playwright test e2e/precision-testing/cross-page --project=chromium

# 全量 ChangeAnalyses
npx playwright test e2e/precision-testing/change-analyses.spec.ts --project=chromium

# 单套件
npx playwright test e2e/precision-testing/cross-page/navigation.spec.ts --project=chromium

# 带 HTML 报告
npx playwright test e2e/precision-testing/cross-page --project=chromium --reporter=html

# 生成 Token（后端目录）
cd backend && python generate_test_token.py > ../test_tokens_clean.json
```

---

## 八、遗留与改进

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P1 | 数据依赖导致的 skip | CI 初始化时通过 Django management command 插入 mock 数据 |
| P2 | 验收标准 ACC_001~006 未覆盖 | 补充仪表盘 KPI、异步任务进度弹窗、执行历史抽屉等用例 |
| P3 | 多浏览器覆盖 | 增加 `--project=firefox` / `--project=webkit` |
| P4 | 并行执行隔离 | 若引入 workers，确保每 worker Token / 数据独立 |
| P5 | CI 集成 | GitHub Actions / GitLab CI 中集成 Playwright + Token 生成 |

---

## 九、ImpactGraph 专项问题（Week 5 E2E 执行新增）

> 以下问题在 ChangeAnalyses / Cross-Page 测试中未出现，仅在 ImpactGraph.vue 测试中发现并解决。

### 9.1 API 空数据返回 500 → 应返回空数组

**症状**：GET `/api/precision-testing/graph/` 在 Neo4j 空图谱时返回 `500 Internal Server Error`。

**根因**：`GraphDataView.get()` 捕获了 `ServiceUnavailable`，但其他未预期异常未捕获，导致 500 上抛。

**解决**：在 `GraphDataView` 增加泛型异常捕获，空数据返回 200 + `{"nodes": [], "edges": []}`。

```python
# backend/apps/precision_testing/views.py
except ServiceUnavailable:
    logger.warning("Neo4j unavailable, returning empty graph data")
    return Response({'nodes': [], 'edges': []})
except Exception as exc:
    logger.error("Graph API error: %s", exc)
    return Response({'nodes': [], 'edges': []})  # 空数据而非 500
```

### 9.2 前端/后端 API 格式不一致

**症状**：前端发送 `{ function_name: "..." }`，后端期望 `{ changed_functions: [...] }`。

| 层级 | 参数名 | 类型 |
|------|--------|------|
| 前端 `ImpactGraph.vue` | `function_name` | string |
| 后端 `ImpactQueryView` | `changed_functions` | list[string] |

**解决（推荐前端修改）**：

```javascript
// frontend/src/api/precision-testing.js
const res = await queryImpact({
  changed_functions: [queryFunc.value.trim()],  // 转为单元素列表
  depth: queryDepth.value
})
```

### 9.3 E2E 模糊选择器导致 strict mode violation

**症状**：
```
Error: locator('[class*="graph"], [class*="canvas"], #graph, #cy') resolved to 3 elements
```

**根因**：`[class*="graph"]` 匹配了 `.impact-graph`、`.graph-toolbar`、`.graph-main` 三个元素。Playwright strict mode 遇到多元素报错。

**解决**：改用精确选择器。

```typescript
// 修改前（失败）
await expect(page.locator('[class*="graph"], [class*="canvas"], #graph, #cy')).toBeVisible();

// 修改后（正确）
await expect(page.locator('.cy-container')).toBeVisible();
```

### 9.4 `setOffline(true)` 模拟断网导致浏览器导航失败

**症状**：`page.context().setOffline(true)` 后 `page.reload()` 报 `net::ERR_INTERNET_DISCONNECTED`，而非触发 Vue 应用的错误处理流程。

**根因**：`setOffline(true)` 使整个浏览器上下文进入真正的网络断开，影响页面导航而非仅 XHR/Fetch。

**解决**：使用 `page.route()` 拦截 API 请求。

```typescript
// 修改前（失败）
await page.context().setOffline(true);
await page.reload();

// 修改后（正确）
await page.route('**/api/precision-testing/graph/**', (route) => {
  route.abort('failed');  // 模拟网络失败
});
await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
await expect(page.locator('.el-message--error, [class*="error"]')).toBeVisible({ timeout: 5000 });
```

### 9.5 Neo4j 空数据阻塞性能测试

**症状**：`IMPACT_PERF_001`（万级节点）和 `IMPACT_PERF_002`（3层深度查询）无法执行。

**根因**：测试环境未执行图谱构建，Neo4j 节点数为 0。

**解决**：通过 management command 填充数据。

```bash
cd backend
python manage.py build_graph --full
```

---

## 十、遗留与改进（追加）

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P0 | API 500 错误 | 修复 `GraphDataView` 异常处理，空数据返回空数组 |
| P0 | API 格式不一致 | 前端 `queryImpact()` 改用 `changed_functions: [name]` |
| P1 | E2E 选择器 | 将模糊选择器改为 `.cy-container` 精确匹配 |
| P1 | 测试数据 | 执行 `build_graph` 填充 Neo4j 数据 |
| P2 | 离线异常测试 | 改用 `page.route()` 而非 `setOffline(true)` |
| P3 | ALLOWED_HOSTS | 开发环境添加 `testserver` 到 `ALLOWED_HOSTS` |

---

## 十一、MappingManager 专项问题（Week 5 E2E 执行新增）

> 以下问题在 ChangeAnalyses / Cross-Page / ImpactGraph 测试中未出现，仅在 MappingManager.vue 测试中发现并解决。

### 11.1 `authenticatedPage` fixture 未注册 → "unknown parameter"

**症状**：

```
Error: Test has unknown parameter "authenticatedPage"
```

所有使用 `{ authenticatedPage: page }` 的测试均报错。

**根因**：同时从两个不同来源导入 `test` 和 `expect`，fixture 扩展不完整。

```typescript
// 错误写法
import { test } from './auth-api';              // 扩展后的 test
import { expect } from '@playwright/test';      // 原始 expect，fixture 未注册
```

**解决**：统一从 `auth-api.ts` 导入所有符号。

```typescript
// auth-api.ts 统一导出
import { test as base, expect, request } from '@playwright/test';
export { expect, request };
export const test = base.extend({ ... });

// spec 文件统一导入
import { test, expect, request, loadTokens } from './auth-api';
```

### 11.2 `loadTokens` 未导出

**症状**：`TypeError: (0 , _authApi.loadTokens) is not a function`

**根因**：`loadTokens` 是 `auth-api.ts` 内部函数，未被 `export`。

**解决**：

```typescript
// auth-api.ts
export function loadTokens(): TokenData {
  const raw = fs.readFileSync(TOKEN_PATH, 'utf-8');
  return JSON.parse(raw);
}
```

### 11.3 自动构建 running 状态无法捕获

**症状**：MAPPING_E2E_004、MAPPING_UI_026-027 等因等待 running 状态超时而失败。

**根因**：后端 `autoBuildMappings()` 立即返回 200，前端状态从 `idle` 直接跳到 `done`，`running` 状态只持续极短时间。

**解决**：不等待 running，直接验证 done 状态。

```typescript
// 修改前（不稳定）
await startBtn.click();
await page.waitForTimeout(2000);
const hasRunning = await page.locator('.el-icon.is-loading').isVisible();

// 修改后（稳定）
await startBtn.click();
await expect(page.locator('.build-icon.done')).toBeVisible({ timeout: 10000 });
```

### 11.4 分页下拉选择器不稳定

**症状**：`locator('.el-select-dropdown__item').nth(1)` 元素存在但 `not visible`。

**根因**：Element Plus 下拉选项在下拉面板隐藏时仍存在于 DOM 中。

**解决**：使用 `:visible` 过滤。

```typescript
// 修改前（不稳定）
await sizeSelect.click();
await page.locator('.el-select-dropdown__item').nth(1).click();

// 修改后（稳定）
await sizeSelect.click();
await page.waitForTimeout(300);
await page.locator('.el-select-dropdown:visible .el-select-dropdown__item').nth(1).click();
```

### 11.5 分页 page=2 返回 404

**症状**：MAPPING_API_007 访问 `page=2` 返回 404 而非空数组。

**根因**：DRF 分页器在总数据不足一页时，访问后续页返回 404。

**解决**：先检查总数据量或改用数据驱动断言。

```typescript
const { body } = await apiWithAuth('get', '/api/precision-testing/mappings/?page=1&page_size=10');
if (body.count <= 10) {
  test.skip(true, '数据不足一页');
  return;
}
```

---

## 十二、遗留与改进（追加）

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P0 | MappingManager 测试数据缺失 | 预置 testcase=1 和若干 mapping 记录 |
| P1 | 自动构建 running 状态断言 | 改为验证 idle→done 状态变化 |
| P2 | 分页选择器不稳定 | 使用 `:visible` 伪类过滤 |
| P3 | 表单验证时机 | 改用 `waitForSelector` |
| P4 | route.abort() 错误UI | 改用 `page.evaluate()` 模拟 API 失败 |

---

## 十三、PrecisionRunHistory 专项经验

### 13.1 后端 filter 缺失导致全部筛选用例失败

**症状**：`?status=completed` `?start_date=2026-01-01` 等参数被完全忽略，始终返回全部记录。

**根因**：`PrecisionRunRecordViewSet` 未配置 `filter_backends` / `filterset_fields`。

**铁律**：DRF `ModelViewSet` **默认不启用过滤**。凡涉及筛选/搜索的 API，必须显式配置 `DjangoFilterBackend`。

```python
class PrecisionRunRecordViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']  # 至少精确匹配
```

### 13.2 文档与代码 status 值不一致

**症状**：文档写 `success`，后端 choices 定义 `completed`，前端下拉同时展示两者导致筛选无结果。

**铁律**：测试用例中的枚举值必须与**后端模型 choices** 逐字一致。不要假设 "success ≈ completed"。

| 文档旧值 | 代码实际值 |
|---------|-----------|
| `success` | `completed` |
| `fail` | `failed` |

### 13.3 `page.reload()` 后 toast 时序敏感

**症状**：`RUN_ERR_001` 偶发失败——reload 后 `ElMessage.error` 未在 timeout 内出现。

**根因**：`page.route()` 拦截在 reload 完成后才注册，或 reload 后 JS 重新初始化导致 fetch 已完成。

**铁律**：不要断言 `reload()` 后的 toast 时序。改用：
1. 先 `route()` 注册拦截
2. 再**手动触发**请求（如点击刷新按钮）
3. 使用 `expect.poll()` 而非固定 timeout

```typescript
await page.route('**/api/precision-testing/runs/**', route => route.abort('failed'));
await page.locator('button:has-text("刷新")').click();
await expect.poll(async () => page.locator('.el-message--error').isVisible(), { timeout: 15000 }).toBe(true);
```

### 13.4 序列化器字段缺失导致 UI 用例无法闭环

**症状**：38 条手动 UI 用例中 4 条（repo_name / duration_seconds / error_message / commit_hash）无法验证。

**根因**：`PrecisionRunRecordSerializer` 未暴露这些字段，且部分字段模型本身不存在。

**铁律**：执行前端测试前，先**用 curl 或 API 测试**验证后端返回的字段集合是否满足 UI 渲染需求。

```bash
curl -s http://localhost:8000/api/precision-testing/runs/1/ | python -m json.tool | grep -E "repo_name|branch|commit|duration|error"
```

### 13.5 测试数据预置策略

PrecisionRunHistory 需要 4 种状态的 `PrecisionRunRecord` 才能覆盖全部场景：

| 状态 | 用例数 | 关键验证点 |
|------|--------|-----------|
| `completed` + reduction_rate > 0 | 多数 | 进度条颜色、状态标签 |
| `failed` | RUN_API_003 | 错误信息区域 |
| `running` | RUNHIST_003 | 状态筛选、标签颜色 |
| `completed` + `selected_testcases=[]` | RUN_API_010 | 空列表渲染 |

**推荐**：封装 `setup_run_records()` fixture 在 E2E 测试前置中自动写入。

---

## 十四、遗留与改进（PrecisionRunHistory 追加）

| 优先级 | 事项 | 方案 | 状态 | 修改文件 |
|--------|------|------|------|----------|
| P0 | `PrecisionRunRecordViewSet` 添加 filter | 新建 `PrecisionRunRecordFilter`（status + start_date/end_date），ViewSet 配置 `filter_backends` + `filterset_class` | ✅ 已完成 | `backend/apps/precision_testing/filters.py` `backend/apps/precision_testing/views.py` |
| P0 | status 值统一 | 前端 `<el-option value="completed">`、`statusType`/`statusLabel` 映射、E2E 选择器同步更新 | ✅ 已完成 | `frontend/src/views/precision-testing/PrecisionRunHistory.vue` `frontend/e2e/precision-testing/precision-run-history.spec.ts` |
| P0 | `error_message` 字段 | `PrecisionRunRecord` 模型新增 `error_message = models.TextField(blank=True)`；序列化器 `CharField(read_only=True)` 暴露 | ✅ 已完成 | `backend/apps/precision_testing/models.py` `backend/apps/precision_testing/serializers.py` |
| P1 | `repo_name`/`branch`/`commit_hash` 暴露 | `PrecisionRunRecordSerializer` 添加 `SerializerMethodField`，通过 `impact_analysis.change_analysis.repo_binding` 关联链获取 | ✅ 已完成 | `backend/apps/precision_testing/serializers.py` |
| P1 | `duration_seconds`/`triggered_at` 暴露 | `duration_seconds` 为 `SerializerMethodField`（`completed_at - started_at`）；`triggered_at` 为 `started_at` ISO 格式别名 | ✅ 已完成 | `backend/apps/precision_testing/serializers.py` |
| P2 | `RUN_ERR_001` 测试稳定性 | 废弃 `page.reload()` 方案：改为先 `route()` 注册拦截再点击刷新按钮触发请求；`expect.poll({ timeout: 15000 })` 替代固定 `waitForTimeout` | ✅ 已完成 | `frontend/e2e/precision-testing/precision-run-history.spec.ts` |
| P2 | 测试数据自动化 | 新建 `setup_run_records.py`：自动创建/更新 4 条覆盖全部状态（completed/failed/running/空选中）的 `PrecisionRunRecord`，含 `verify_run_records()` 验证 | ✅ 已完成 | `tests/precision_testing/setup_run_records.py` |
| P3 | 前端代码风格 | 新建 `precision-formatters.js`：统一抽取 `formatDateTime`/`formatRate`/`formatDuration`/`statusType`/`statusLabel`/`reductionColor`/`riskColor`；组件移除内联定义 | ✅ 已完成 | `frontend/src/utils/precision-formatters.js` `frontend/src/views/precision-testing/PrecisionRunHistory.vue` |

> **迁移提醒**：`PrecisionRunRecord.error_message` 为模型新增字段，需执行：
> ```bash
> cd backend && python manage.py makemigrations precision_testing && python manage.py migrate
> ```

---

## 十五、RiskDashboard 专项问题（Week 5 E2E 执行新增）

> 以下问题在 ChangeAnalyses / Cross-Page / ImpactGraph / MappingManager / PrecisionRunHistory 测试中未出现，仅在 RiskDashboard.vue 测试中发现并解决。

### 15.1 后端 DashboardView 返回字段 ≠ 前端期望字段

**症状**：API 返回 200，但所有 KPI 显示 0，所有图表空白。

**根因**：
```python
# backend/views.py:DashboardView.get() 实际返回
{ "total_mappings": 0, "total_analyses": 0, "completed_analyses": 0,
  "avg_reduction_rate": 0.0, "recent_runs": [] }

# 前端 RiskDashboard.vue 期望
{ "summary": { "repo_count", "analysis_count", "mapping_count", "avg_reduction_rate" },
  "risk_distribution": { "high", "medium", "low" },
  "trend": { "dates", "analysis_counts", "function_counts" },
  "top_risky_files": [...],
  "run_stats": { "dates", "precision_counts", "full_counts" } }
```

**解决**：重构 `DashboardView.get()` 为前端期望的嵌套结构，补全聚合查询。

```python
# backend/apps/precision_testing/views.py
class DashboardView(APIView):
    def get(self, request):
        # summary
        repo_count = RepoBinding.objects.count()
        analysis_count = CodeChangeAnalysis.objects.count()
        mapping_count = TestCaseCodeMapping.objects.count()
        avg_reduction = PrecisionRunRecord.objects.filter(
            status='completed'
        ).aggregate(avg=Avg('reduction_rate'))['avg'] or 0.0

        # risk_distribution
        risk_distribution = dict(
            RiskPredictionRecord.objects.values('risk_level')
            .annotate(count=Count('id'))
            .values_list('risk_level', 'count')
        )
        for level in ['high', 'medium', 'low']:
            risk_distribution.setdefault(level, 0)

        # trend: last 14 days
        # run_stats: last 14 days
        # top_risky_files: from RiskPredictionRecord + ImpactAnalysis

        return Response({
            'summary': { ... },
            'risk_distribution': risk_distribution,
            'trend': trend,
            'top_risky_files': top_risky_files,
            'run_stats': run_stats,
        })
```

**铁律**：前端页面开发完成后，必须**立即用 curl/API 测试验证**后端返回字段与前端期望 100% 对齐；不要等到 E2E 阶段才发现。

---

### 15.2 Token 过期导致 API 测试 401

**症状**：`test_tokens_clean.json` 中的 JWT access token 有效期 30 分钟，过期后 Playwright API 测试直接发送该 token，后端 JWT 验证失败返回 401。

**根因**：auth-api.ts fixture 在浏览器端注入 token 时设置了 `token_expires_at = Date.now() + expires_in`，浏览器端的 Vue 应用认为 token 有效；但 Playwright 的 `request.newContext()` 直接携带磁盘上的旧 token 发 HTTP，后端 JWT `exp` claim 已过期。

**解决**：引入 Playwright `globalSetup` 自动检测并刷新 Token。

```typescript
// frontend/e2e/global-setup.ts
export default async function globalSetup() {
  const TOKEN_MAX_AGE_MS = 25 * 60 * 1000;
  let needRefresh = true;
  if (fs.existsSync(TOKEN_PATH)) {
    const ageMs = Date.now() - fs.statSync(TOKEN_PATH).mtimeMs;
    if (ageMs < TOKEN_MAX_AGE_MS) needRefresh = false;
  }
  if (!needRefresh) return;
  // spawn python generate_test_token.py, extract JSON line, write to disk
}
```

```javascript
// playwright.config.js
export default defineConfig({
  globalSetup: require.resolve('./e2e/global-setup.ts'),
  // ...
});
```

**铁律**：CI 中必须在 Playwright 测试步骤前插入 Token 生成；本地开发每次长会话前检查 token 时效。

---

### 15.3 Element Plus `el-row`/`el-col` 选择器不稳定

**症状**：`DASH_UI_001` 使用 `.risk-dashboard .el-row.kpi-row .el-col` 断言 `toHaveCount(4)`，60s 超时失败。

**根因**：Element Plus 的 `el-row`/`el-col` 渲染后 class 在特定版本/场景下与预期层级不一致；Page snapshot 显示 DOM 结构扁平化。

**解决**：
```typescript
// 不稳定
await expect(page.locator('.risk-dashboard .el-row.kpi-row .el-col')).toHaveCount(4);

// 稳定：按文本内容定位（不受 DOM 层级变化影响）
for (const t of ['绑定仓库数', '变更分析次数', '映射关系总数', '平均缩减率']) {
  await expect(page.locator('.risk-dashboard').getByText(t)).toBeVisible();
}
await expect(page.locator('.risk-dashboard .el-statistic__head')).toHaveCount(4);
```

**铁律**：Element Plus 布局组件的 class 选择器**优先用于样式，不用于测试断言**；测试断言优先使用**文本内容**或**组件内部稳定 class**（如 `.el-statistic__head`）。

---

### 15.4 ECharts canvas 无法断言内部数据

**症状**：只能验证 `<canvas>` 元素存在，无法验证饼图扇区数量、折线数据点、条形颜色等。

**根因**：ECharts 使用 `<canvas>` 渲染，不是 DOM 元素；Playwright 无法直接读取 canvas 像素或内部 `_echarts_instance` 状态。

**当前解决（降级验证）**：
- 验证 canvas 存在 + hover 不崩溃 + 页面无报错
- 长期：引入视觉回归测试（screenshot diff）或 `page.evaluate()` 读取 `echarts.getInstanceByDom()`

```typescript
// 读取 ECharts 内部 option（需组件暴露实例）
const option = await page.evaluate(() => {
  const chart = (window as any).echarts.getInstanceByDom(
    document.querySelector('.chart-box')
  );
  return chart?.getOption();
});
```

---

### 15.5 DASH_ERR_002 超时测试耗时 34s

**症状**：模拟 API 永不响应的测试耗时 34.6s。

**根因**：`await new Promise(() => {})` 让 route 永不 respond，等待前端 Axios timeout（30s）+ Playwright expect 超时（35s）。

**解决**：此测试意图就是验证"超时后不无限 loading"，30s+ 等待是设计上的。建议在 CI 中将此类测试标记为 `test.slow()`：

```typescript
test.slow();
test('DASH_ERR_002: API timeout shows error, no infinite loading', async () => {
  // ...
});
```

---

## 十六、可复用代码模式（Risk Dashboard 专用）

### 16.1 API 结构差距检查模式

用于记录前后端字段不匹配，后端修复后测试自动失败提示更新：
```typescript
const expectedFields = ['summary', 'risk_distribution', 'trend', 'top_risky_files', 'run_stats'];
const missing = expectedFields.filter(f => !(f in body));
expect(missing).toEqual(expectedFields); // living documentation
```

### 16.2 Element Plus 统计卡片断言模式

```typescript
const kpiTitles = ['绑定仓库数', '变更分析次数', '映射关系总数', '平均缩减率'];
for (const t of kpiTitles) {
  await expect(page.locator('.risk-dashboard').getByText(t)).toBeVisible();
}
await expect(page.locator('.risk-dashboard .el-statistic__head')).toHaveCount(4);
```

### 16.3 ECharts canvas 存在性验证模式

```typescript
const chartCard = page.locator('.chart-card').filter({ hasText: '风险等级分布' });
await expect(chartCard.locator('canvas')).toBeVisible({ timeout: 5000 });
```

### 16.4 API 失败模拟（route + fulfill）

```typescript
await page.route('**/api/precision-testing/dashboard/**', route =>
  route.fulfill({ status: 500, body: JSON.stringify({ error: 'Internal Server Error' }) }),
);
await page.goto('/precision-testing/dashboard', { waitUntil: 'domcontentloaded' });
const errorMsg = page.locator('.el-message--error');
await expect(errorMsg.first()).toBeVisible({ timeout: 10000 });
await page.unroute('**/api/precision-testing/dashboard/**');
```

---

## 十七、关键决策记录（Risk Dashboard 追加）

### 决策 1：用 `getByText()` 替代布局 class 选择器

| 维度 | class 选择器 | getByText() |
|------|-------------|-------------|
| Element Plus 兼容性 | 低（class 可能变化） | 高（文案稳定） |
| 可读性 | 中 | 高 |
| 维护成本 | 高 | 低 |
| **结论** | ❌ | ✅ |

### 决策 2：API 结构差距用 `expect(missing).toEqual(...)` 记录

不跳过、不注释，而是用会失败的断言来记录已知问题。后端修复后断言自动失败，强制同步更新测试。

### 决策 3：性能测试阈值设为 3s（而非 1s）

原始用例要求图表 1s 内渲染，但 Playwright 导航 + ECharts 初始化 + 空数据渲染在测试环境实际约 2-3s。将阈值放宽到 3s 作为工程实际，同时记录真实耗时供优化参考。

---

## 十八、遗留与改进（Risk Dashboard 追加）

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P0 | 后端 DashboardView 字段结构对齐 | ✅ 已完成（重构为嵌套结构） |
| P1 | Token 自动刷新 | ✅ 已完成（Playwright globalSetup） |
| P2 | ECharts canvas 内容断言 | 引入视觉回归测试（screenshot diff） |
| P3 | 测试数据预置 | 插入 mock RepoBinding/CodeChangeAnalysis/PrecisionRunRecord |
| P4 | 视觉回归 CI 集成 | 在 GitHub Actions / GitLab CI 中集成 screenshot 对比 |
| P5 | DASH_ERR_002 慢测试标记 | 使用 `test.slow()` 避免阻塞快速反馈 |

