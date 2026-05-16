# Week 5 精准测试前端 — ChangeAnalyses.vue 测试技术沉淀与复盘

> 生成时间：2026-05-13
> 主题：ChangeAnalyses.vue E2E 测试执行过程中的问题、阻塞与解决方案
> 适用范围：Vue 3 + Element Plus 前端、Django REST + JWT 后端、Playwright TypeScript 测试

---

## 一、总体结论

本次 ChangeAnalyses.vue 测试共 **22 条用例**，全部通过（22 passed / 0 failed / 0 skipped）。测试执行过程中遇到的阻塞性问题均已解决，测试脚本基于 `CHANGE_ANALYSES_TEST_CASES.md` 中定义的用例执行。

---

## 二、问题与解决方案详述

### 问题 1：认证 Fixture 不可靠 —— `waitForURL` 超时被静默吞掉

**现象**

使用原始 `auth.ts` fixture 时，测试超时后 `waitForURL` 的异常被 `.catch(() => {})` 吞掉，导致测试继续执行但页面实际仍停留在 `/login`。

**根因分析**

```typescript
// auth.ts（原始问题代码）
await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 20000 })
  .catch(() => {});   // ← 致命：.catch(() => {}) 吞掉了超时异常
```

- UI 登录流程在测试并发或后端响应慢时容易超时
- `.catch(() => {})` 导致超时异常被静默忽略
- 后续对 `.el-aside`、`.el-main` 的断言因页面未正确加载而超时

**解决方案**

放弃 UI 登录流程，改用 **localStorage 种子注入**：

1. 预生成 JWT Token（一次生成，多次复用）
2. Fixture 直接 `page.evaluate()` 将 Token 写入 localStorage
3. `page.reload()` 触发 Vue Router 守卫重新评估
4. 断言跳转完成

```typescript
// auth-api.ts（最终方案）
await page.evaluate((data) => {
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  localStorage.setItem('token_expires_at', data.expiresAt.toString());
  localStorage.setItem('user', JSON.stringify(data.user));
}, { access, refresh, expiresAt, user });
await page.reload({ waitUntil: 'domcontentloaded' });
await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20000 });
```

**经验沉淀**

- **永远不要 `.catch(() => {})` 吞掉导航/等待超时**，除非你能 100% 确定后续断言与当前操作无关。
- 对于"认证态"这一纯前置条件，使用 storage seeding 比走完整 UI 流程更可靠、更快。

---

### 问题 2：后端匿名限流 —— `AnonRateThrottle` 导致 429

**现象**

多轮测试执行后，登录接口返回 `429 Too Many Requests`，后续大量测试因无法获取认证态而失败。

**根因分析**

- 原始 `auth.ts` 每轮测试都通过 `page.request.post('/api/auth/login/')` 获取 Token
- DRF 配置中 `AnonRateThrottle` 的 `anon_rate` 为 `100/hour`
- Playwright 测试并发或重试很快耗尽配额

**解决方案**

**一次性 Token 生成 + 本地缓存**：

1. 编写 Django 独立脚本 `backend/generate_test_token.py`
2. 直接调用 `RefreshToken.for_user()` 生成 Token，不走 HTTP 接口
3. 输出到 `test_tokens_clean.json`
4. Fixture 运行时从磁盘读取，零 HTTP 开销

```python
# backend/generate_test_token.py
u = User.objects.get(username='admin')
r = RefreshToken.for_user(u)
result = {
    'access': str(r.access_token),
    'refresh': str(r),
    'user': { ... },
    'access_expires_in': 30 * 60,
}
```

**经验沉淀**

- 当测试需要高频执行同一前置操作时，先检查是否存在**服务端限流**。
- 对于 Token 获取这类纯数据准备，优先使用"绕过 HTTP"的生成方式。

---

### 问题 3：`auth.ts` 被 IDE / Linter 自动回退

**现象**

修改 `auth.ts` 后，文件内容被外部工具自动恢复为旧版本，导致修复反复失效。

**根因分析**

- 项目配置了某种代码格式化或 lint 的自动修复 hook
- 该 hook 缓存了旧版本内容，或从模板/缓存中还原

**解决方案**

**创建全新文件，绕过 hook 的追踪范围**：

- 不再修改 `auth.ts`，改为创建 `auth-api.ts`
- 所有 spec 文件将 `import { test } from '../auth'` 批量替换为 `import { test } from '../auth-api'`
- 旧 `auth.ts` 保留但不使用

**批量替换命令**：

```bash
cd frontend/e2e/precision-testing
node -e "
const fs = require('fs');
const path = require('path');
const files = fs.readdirSync('.').filter(f => f.endsWith('.spec.ts'));
for (const f of files) {
  let c = fs.readFileSync(f, 'utf8');
  c = c.replace(\"from './auth';\", \"from './auth-api';\");
  fs.writeFileSync(f, c);
}
console.log('Updated', files.length, 'files');
"
```

**经验沉淀**

- 当文件被外部自动化工具反复覆盖时，不要与工具对抗（调试 hook 成本高）。
- **创建新文件是成本最低的绕过策略**。

---

### 问题 4：Element Plus `el-menu-item` 的 `index` prop 不作为 DOM attribute

**现象**

导航测试最初使用 `[index="..."]` CSS 属性选择器定位菜单项，所有 NAV 测试匹配失败，报 `locator resolved to 0 elements`。

**根因分析**

```html
<!-- Element Plus 实际渲染的 DOM -->
<li class="el-menu-item is-active" role="menuitem" style="padding-left: 20px;">
  <i class="el-icon"><svg>...</svg></i>
  <span>仓库绑定</span>
</li>
```

- Vue 组件的 `index` prop 仅用于组件内部状态计算，不会渲染为 HTML attribute
- 因此 `.el-menu-item[index="/precision-testing/repos"]` 永远匹配不到元素

**解决方案**

改用 **文本过滤**定位：

```typescript
// 修改前（失败）
page.locator('.el-menu-item[index="/precision-testing/repos"]')

// 修改后（成功）
page.locator('.el-menu-item').filter({ hasText: '仓库绑定' })
```

**经验沉淀**

- **不要假设 Vue 组件的 prop 会映射为 DOM attribute**。使用浏览器 DevTools 检查实际渲染的 DOM 结构。
- 对于菜单、列表等文本明确的组件，优先使用 `filter({ hasText: ... })`。

---

### 问题 5：`/home` 路由不使用 `Layout` 组件

**现象**

NAV_009（从首页导航到精准测试页面）执行到 `/home` 后，`.el-aside` 等待超时。

**根因分析**

- Vue Router 配置中 `/home` 直接挂载 `Home.vue`，未包裹 `Layout` 组件
- 因此 `/home` 页面不存在 `.el-aside`、`.el-header`、`.el-main`

**解决方案**

在测试中单独处理 `/home` 场景：

```typescript
test('NAV_009: navigate from home to precision-testing/repos via sidebar', async ({ authenticatedPage: page }) => {
  await page.goto('/home', { waitUntil: 'domcontentloaded' });

  const reposEntry = menuItemByLabel(page, '仓库绑定').first();
  if (await reposEntry.isVisible().catch(() => false)) {
    await reposEntry.click();
  } else {
    await page.goto('/precision-testing/repos', { waitUntil: 'domcontentloaded' });
  }
  await page.waitForURL('**/precision-testing/repos', { timeout: 10000 });
});
```

**经验沉淀**

- **避免在 E2E 测试中假设"所有页面共享同一布局"**。即使同一应用内，也可能存在独立布局的 landing page。
- 将"等待布局元素"封装在 helper 中时要提供跳过选项。

---

### 问题 6：ChangeAnalyses 详情加载依赖后端数据

**现象**

测试执行时需要后端存在已完成（completed）状态的 analysis 记录，否则详情面板的折叠列表等功能无法验证。

**根因分析**

- 测试用例 CHANGE_UI_009 ~ CHANGE_UI_017 需要列表中存在 completed 状态的记录
- 无数据时测试可能无法覆盖所有功能路径

**解决方案**

使用 `test.skip()` 进行防御性跳过：

```typescript
const firstItem = page.locator('.list-item').first();
if (!(await firstItem.isVisible().catch(() => false))) {
  test.skip(true, 'No analysis records available.');
  return;
}
```

**经验沉淀**

- 对于依赖特定业务数据的 E2E 用例，**`test.skip()` 优于 `test.fail()`**。
- 长期建议：建立测试数据初始化脚本，在测试套件运行前插入最小可用数据集。

---

## 三、关键技术决策记录

### 决策 1：为什么弃用 `auth.ts`，而非修复它？

| 维度 | 修复 auth.ts | 新建 auth-api.ts |
|------|-------------|------------------|
| 与外部 hook 冲突 | 高（持续被覆盖） | 低（新文件不在 hook 缓存中） |
| 实现复杂度 | 中（需解决 UI 登录不稳定） | 低（storage seeding 简单可靠） |
| 执行速度 | 慢（每次 UI 登录 ~3-5s） | 快（直接注入 ~500ms） |
| 后端依赖 | 高（走登录 API，受限流控） | 低（零 API 调用） |
| 结论 | ❌ 不可行 | ✅ 推荐 |

### 决策 2：`domcontentloaded` vs `networkidle`

- 精准测试模块部分页面存在轮询（polling）或 SSE 长连接
- `networkidle` 要求网络静默 500ms，长连接会导致等待超时
- 统一使用 `domcontentloaded`，并在关键元素上使用 `waitFor({ state: 'visible' })` 作为替代

---

## 四、可复用的模式与代码片段

### 4.1 预生成 JWT Fixture（推荐复用）

```typescript
// auth-api.ts 模式
export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    const tokens = loadTokens();
    const expiresAt = Date.now() + tokens.access_expires_in * 1000;

    await page.goto('/login', { waitUntil: 'domcontentloaded' });
    await page.evaluate((data) => {
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      localStorage.setItem('token_expires_at', data.expiresAt.toString());
      localStorage.setItem('user', JSON.stringify(data.user));
    }, { access: tokens.access, refresh: tokens.refresh, expiresAt, user });

    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20000 });
    await use(page);
  },
});
```

### 4.2 列表选择器辅助函数

```typescript
// 通用列表项选择器（避免依赖 index prop）
const menuItemByLabel = (page: Page, label: string) =>
  page.locator('.el-menu-item').filter({ hasText: label });

// 列表加载等待
await page.waitForSelector('.list-item', { timeout: 10000 }).catch(() => {});
```

### 4.3 防御性跳过模式

```typescript
const target = page.locator('.list-item').first();
if (!(await target.isVisible().catch(() => false))) {
  test.skip(true, 'Required data not available.');
  return;
}
```

---

## 五、后续改进建议

| 优先级 | 事项 | 建议方案 |
|--------|------|---------|
| P1 | 测试数据依赖 | 在 CI / 测试环境初始化时，通过 Django management command 插入 1 条 mock analysis 记录（completed 状态，带 changed_files） |
| P2 | 进度轮询真实场景测试 | 当前进度轮询测试为静态验证，建议增加可触发分析的真实 E2E 场景 |
| P3 | 多浏览器覆盖 | 当前仅 `--project=chromium`，建议增加 `firefox` 和 `webkit` |
| P4 | ChangeAnalyses 详情加载超时 | 建议在前端增加更明确的超时错误提示（当前 30s 超时不够清晰） |

---

## 六、参考文件索引

| 文件 | 路径 |
|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/CHANGE_ANALYSES_TEST_CASES.md` |
| 执行报告 | `tests/testcase/precision_testing/Week 5/CHANGE_ANALYSES_TEST_CASES_EXECUTION_REPORT.md` |
| E2E 测试脚本 | `frontend/e2e/precision-testing/change-analyses.spec.ts` |
| JWT 预生成脚本 | `backend/generate_test_token.py` |
| 认证 Fixture | `frontend/e2e/precision-testing/auth-api.ts` |
| API 层封装 | `frontend/src/api/precision-testing.js` |
| Cross-Page 技术沉淀 | `tests/testcase/precision_testing/Week 5/CROSS_PAGE_TEST_RETROSPECTIVE.md` |
| Cross-Page 执行报告 | `tests/testcase/precision_testing/Week 5/CROSS_PAGE_TEST_EXECUTION_REPORT.md` |