# Week 5 精准测试前端 — Cross-Page E2E 测试执行报告

> 生成时间：2026-05-13
> 测试范围：CROSS_PAGE_TEST_CASES.md 中定义的全部 6 大类测试（NAV / AUTH / API_SHARE / LAYOUT / PAGE / SEC）
> 执行框架：Playwright + TypeScript
> 前端地址：http://localhost:3000（Vue 3 + Element Plus）
> 后端地址：http://localhost:8000（Django REST Framework + JWT）

---

## 一、执行概览

| 指标 | 数值 |
|------|------|
| 测试套件（Spec 文件） | 6 个 |
| 总用例数 | 41 条 |
| **通过** | **38** |
| **跳过** | **3** |
| **失败** | **0** |
| 整体耗时 | ~2.4 分钟（全量） |

> 注：3 条跳过用例为 `PAGE_001`、`PAGE_002`、`PAGE_003` 中的前两条，因测试环境无已绑定的可分析仓库，缺乏前置数据，自动 skip 而非失败。

---

## 二、测试脚本清单

所有脚本位于 `frontend/e2e/precision-testing/cross-page/` 目录。

| # | 脚本文件 | 覆盖用例 | 用例数 | 结果 |
|---|---------|---------|--------|------|
| 1 | `navigation.spec.ts` | NAV_001 ~ NAV_010 | 10 | 10 passed |
| 2 | `auth-session.spec.ts` | AUTH_001 ~ AUTH_005 | 5 | 5 passed |
| 3 | `api-shared.spec.ts` | API_SHARE_001 ~ API_SHARE_008 | 8 | 8 passed |
| 4 | `layout.spec.ts` | LAYOUT_001 ~ LAYOUT_005 | 5 | 5 passed |
| 5 | `page-flow.spec.ts` | PAGE_001 ~ PAGE_003 | 3 | 1 passed, 2 skipped |
| 6 | `security.spec.ts` | SEC_001 ~ SEC_010 | 10 | 10 passed |

### 2.1 公共 Fixture

| 文件 | 路径 | 作用 |
|------|------|------|
| `auth-api.ts` | `frontend/e2e/precision-testing/auth-api.ts` | 自定义 Playwright fixture `authenticatedPage`，通过预生成 JWT 种子直接写入 localStorage，绕过 UI 登录流程，避免后端限流 |

---

## 三、测试数据与环境准备

### 3.1 预生成 JWT Token

为避免每次测试调用 `/api/auth/login/` 触发后端 `AnonRateThrottle`（匿名 100/hour），采用一次性 Token 生成策略：

- **生成脚本**：`backend/generate_test_token.py`
- **输出文件**：`E:/testhub_platform/test_tokens_clean.json`
- **生成方式**：直接调用 Django ORM + `rest_framework_simplejwt.tokens.RefreshToken.for_user()`，无需走 HTTP API
- **Token 内容**：
  - `access`：JWT Access Token
  - `refresh`：JWT Refresh Token
  - `user`：用户对象（id, username, email, avatar, is_active 等）
  - `access_expires_in`：1800 秒（30 分钟）
  - `refresh_expires_in`：604800 秒（7 天）

### 3.2 Fixture 注入逻辑

`auth-api.ts` 中的 `authenticatedPage` 执行步骤：

1. `page.goto('/login')` 加载登录页
2. `page.evaluate()` 将 Token 与用户信息写入 localStorage：
   - `access_token`
   - `refresh_token`
   - `token_expires_at`
   - `user`
3. `page.reload()` 触发 Vue Router 守卫重新评估认证状态
4. `page.waitForURL((url) => !url.toString().includes('/login'))` 等待重定向完成

### 3.3 测试账号

| 字段 | 值 |
|------|-----|
| username | `admin` |
| password | `admin123456` |

---

## 四、分套件执行结果

### 4.1 Navigation & Routing（导航与路由）

**文件**：`navigation.spec.ts`  
**结果**：10 passed / 0 failed / 0 skipped  
**耗时**：~48s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| NAV_001 | 侧边栏显示 6 个精准测试菜单入口 | passed | 6.9s |
| NAV_002 | 每个菜单项有图标（el-icon） | passed | 3.1s |
| NAV_003 | 当前页面菜单项高亮（is-active） | passed | 4.1s |
| NAV_004 | 点击同级菜单切换高亮 | passed | 4.0s |
| NAV_005 | 面包屑显示模块名"精准测试" | passed | 3.1s |
| NAV_006 | 面包屑显示页面标题"仓库绑定" | passed | 4.1s |
| NAV_007 | 6 个页面面包屑标题映射正确 | passed | 10.1s |
| NAV_008 | 所有页面可直接 URL 访问 | passed | 10.4s |
| NAV_009 | 从首页可导航到精准测试页面 | passed | 5.1s |
| NAV_010 | 快速切换菜单不破坏路由 | passed | 3.9s |

**关键技术点**：
- 使用 `page.locator('.el-menu-item').filter({ hasText: label })` 定位菜单项，避免 Element Plus `index` prop 不渲染为 DOM attribute 的问题。
- `/home` 路由不使用 `Layout` 组件，NAV_009 中未对 `.el-aside` 做强制等待。

---

### 4.2 Authentication & Session（认证与会话）

**文件**：`auth-session.spec.ts`  
**结果**：5 passed / 0 failed / 0 skipped  
**耗时**：~16s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| AUTH_001 | 未登录访问重定向到 /login | passed | 1.8s |
| AUTH_003 | Token 过期/无效重定向到 /login | passed | 2.8s |
| AUTH_002 | 已登录可正常访问 /precision-testing/repos | passed | 3.3s |
| AUTH_004 | RepoBindings 页面 API 携带 Bearer Token | passed | 4.7s |
| AUTH_005 | ChangeAnalyses 页面 API 携带 Bearer Token | passed | 4.8s |

**关键技术点**：
- 未登录测试使用 `context.clearCookies()` + `page.addInitScript(() => localStorage.clear())` 彻底清理认证状态。
- 已登录测试复用 `auth-api.ts` 的 `authenticatedPage` fixture。
- Token 校验通过 `page.on('request', ...)` 拦截请求并检查 `authorization` header。

---

### 4.3 API Shared Layer（API 共享层）

**文件**：`api-shared.spec.ts`  
**结果**：8 passed / 0 failed / 0 skipped  
**耗时**：~66s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| API_SHARE_001 | 所有请求 baseURL 为 `/api` | passed | 7.5s |
| API_SHARE_002 | axios timeout = 30000ms | passed | 5.8s |
| API_SHARE_003 | precision-testing.js 导出全部 20 个 API 函数 | passed | 3.8s |
| API_SHARE_004 | 列表 API 分页参数 `page=1&page_size=N` | passed | 6.0s |
| API_SHARE_005 | 任务型端点返回 `analysis_id` / `task_id` | passed | 6.7s |
| API_SHARE_006 | 请求拦截器自动注入 Authorization Bearer | passed | 5.9s |
| API_SHARE_007 | API 返回 401 自动 logout 并跳转 /login | passed | 5.7s |
| API_SHARE_008 | API 失败弹出 ElMessage error toast | passed | 4.1s |

**关键技术点**：
- API_SHARE_002 通过 `page.request.get('/src/utils/api.js')` 读取源码并断言包含 `timeout: 30000`。
- API_SHARE_003 通过请求源码文件并正则匹配 `export function {name}` 验证 20 个函数全部导出。
- API_SHARE_005 优先从页面点击"触发分析"获取响应，无可用仓库时降级为直接调用 API。
- API_SHARE_008 使用 `page.route('**/api/precision-testing/**', route => route.abort('failed'))` 强制 API 失败，验证 UI 侧错误提示。

---

### 4.4 Layout & Responsive（布局与响应式）

**文件**：`layout.spec.ts`  
**结果**：5 passed / 0 failed / 0 skipped  
**耗时**：~16s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| LAYOUT_001 | 使用 Layout（aside + main + header） | passed | 3.2s |
| LAYOUT_002 | 主内容区 padding >= 16px | passed | 3.6s |
| LAYOUT_003 | 1920px 宽度下无横向溢出 | passed | 3.2s |
| LAYOUT_004 | 1024px 宽度下无横向溢出 | passed | 3.1s |
| LAYOUT_005 | 1366px 宽度下左右分栏正常 | passed | 3.0s |

**关键技术点**：
- 使用 `page.evaluate(() => document.body.scrollWidth > document.documentElement.clientWidth + 8)` 检测横向溢出。
- padding 通过 `getComputedStyle` 读取并断言四边均 >= 16px。

---

### 4.5 Cross-Page Data Flow（跨页面数据流）

**文件**：`page-flow.spec.ts`  
**结果**：1 passed / 0 failed / 2 skipped  
**耗时**：~28s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| PAGE_001 | 仓库绑定触发分析 → 记录出现在变更分析 | **skipped** | — |
| PAGE_002 | 触发分析后"最近分析"时间更新 | **skipped** | — |
| PAGE_003 | 页面刷新后瞬态状态重置（无 keep-alive） | passed | 6.4s |

**跳过原因**：
- PAGE_001、PAGE_002 需要测试环境中存在至少一条已绑定的、可触发分析的仓库记录。当前环境无此数据，测试在检测到无"触发分析"按钮时自动 `test.skip()`。

**关键技术点**：
- PAGE_003 在搜索框输入 `keep-alive-probe` 后刷新页面，断言输入值被清空，验证页面未使用 keep-alive 缓存状态。

---

### 4.6 Security（API 安全）

**文件**：`security.spec.ts`  
**结果**：10 passed / 0 failed / 0 skipped  
**耗时**：~15s

| 用例ID | 描述 | 结果 | 耗时 |
|--------|------|------|------|
| SEC_001 | GET /repos/ 无 Token → 401 | passed | 1.1s |
| SEC_002 | GET /analyses/ 无 Token → 401 | passed | 1.6s |
| SEC_003 | GET /mappings/ 无 Token → 401 | passed | 4.0s |
| SEC_004 | GET /graph/ 无 Token → 401 | passed | 0.7s |
| SEC_005 | GET /dashboard/ 无 Token → 401 | passed | 0.5s |
| SEC_006 | GET /runs/ 无 Token → 401 | passed | 1.3s |
| SEC_007 | POST /repos/ 无 Token → 401 | passed | 0.8s |
| SEC_008 | DELETE /mappings/1/ 无 Token → 401 | passed | 0.4s |
| SEC_009 | POST /impact/query/ 无 Token → 401 | passed | 0.3s |
| SEC_010 | POST /repos/1/analyze/ 无 Token → 401 | passed | 1.1s |

**关键技术点**：
- 安全测试完全不依赖浏览器页面，使用 Playwright 的 `request.newContext()` 直接向后端发 HTTP 请求。
- 接受 401 或 403 作为合法未授权响应，严格拒绝 5xx。
- 每个请求使用独立 `request` context，确保无 Cookie / Token 残留。

---

## 五、执行命令参考

```bash
# 进入前端目录
cd frontend

# 安装依赖（如尚未安装）
npm ci

# 全量执行 Cross-Page 测试
npx playwright test e2e/precision-testing/cross-page --project=chromium

# 单独执行某一套件
npx playwright test e2e/precision-testing/cross-page/navigation.spec.ts --project=chromium
npx playwright test e2e/precision-testing/cross-page/security.spec.ts --project=chromium

# 带报告输出
npx playwright test e2e/precision-testing/cross-page --project=chromium --reporter=html
```

---

## 六、遗留事项

| 事项 | 说明 | 建议 |
|------|------|------|
| PAGE_001 / PAGE_002 数据依赖 | 需要预置至少 1 条可分析的仓库绑定 | 在测试数据库 seed 脚本中插入 mock repo binding，或提供专用测试数据初始化接口 |
| 未覆盖 ACC_001 ~ ACC_006 | 验收标准测试用例在原测试计划中定义，但当前 Week 5 测试套件未实现 | 若需完整验收覆盖，可基于现有 auth-api fixture 补充 ACC 用例 |

---

## 七、附件

| 文件 | 路径 | 说明 |
|------|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/CROSS_PAGE_TEST_CASES.md` | 原始需求 |
| JWT 生成脚本 | `backend/generate_test_token.py` | Token 预生成工具 |
| Token 缓存 | `test_tokens_clean.json` | 预生成 JWT（运行时读取） |
| 公共 Fixture | `frontend/e2e/precision-testing/auth-api.ts` | 认证状态注入 |
| 原始 Fixture | `frontend/e2e/precision-testing/auth.ts` | 旧版（UI 登录方式，已废弃） |
