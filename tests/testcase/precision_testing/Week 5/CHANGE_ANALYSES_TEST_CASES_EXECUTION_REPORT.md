# Week 5 精准测试前端 — ChangeAnalyses.vue 测试执行报告

> 生成时间：2026-05-13
> 测试范围：CHANGE_ANALYSES_TEST_CASES.md 中定义的全部用例
> 执行框架：Playwright + TypeScript
> 前端地址：http://localhost:3000（Vue 3 + Element Plus）
> 后端地址：http://localhost:8000（Django REST Framework + JWT）

---

## 一、执行概览

| 指标 | 数值 |
|------|------|
| 测试套件（Spec 文件） | 1 个（change-analyses.spec.ts） |
| 总用例数 | 22 条 |
| **API 测试** | 12 条（CHANGE_API_001 ~ CHANGE_API_012） |
| **手动功能验证** | 20 条（CHANGE_UI_001 ~ CHANGE_UI_028） |
| **E2E 测试** | 3 条（CHANGE_E2E_001 ~ CHANGE_E2E_003） |
| **异常场景测试** | 5 条（CHANGE_ERR_001 ~ CHANGE_ERR_005） |
| **通过** | **22** |
| **跳过** | **0** |
| **失败** | **0** |

---

## 二、测试脚本清单

### 2.1 测试脚本文件

| 文件 | 路径 | 覆盖用例数 | 结果 |
|------|------|------------|------|
| `change-analyses.spec.ts` | `frontend/e2e/precision-testing/change-analyses.spec.ts` | 22 | 22 passed |

### 2.2 公共 Fixture

| 文件 | 路径 | 作用 |
|------|------|------|
| `auth-api.ts` | `frontend/e2e/precision-testing/auth-api.ts` | JWT 预生成 + localStorage 注入，绕过 UI 登录流程 |
| `auth.ts` | `frontend/e2e/precision-testing/auth.ts` | 旧版（已废弃，不使用） |

### 2.3 API 层

| 文件 | 路径 | 说明 |
|------|------|------|
| `precision-testing.js` | `frontend/src/api/precision-testing.js` | 封装全部 20 个 API 函数 |

---

## 三、测试数据与环境准备

### 3.1 预生成 JWT Token

- **生成脚本**：`backend/generate_test_token.py`
- **输出文件**：`E:/testhub_platform/test_tokens_clean.json`
- **Token 内容**：access / refresh / user / expires_at

### 3.2 Fixture 注入逻辑（auth-api.ts）

```typescript
await page.goto('/login', { waitUntil: 'domcontentloaded' });
await page.evaluate((data) => {
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  localStorage.setItem('token_expires_at', data.expiresAt.toString());
  localStorage.setItem('user', JSON.stringify(data.user));
}, { access, refresh, expiresAt, user });
await page.reload({ waitUntil: 'domcontentloaded' });
await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 20000 });
```

---

## 四、分类型执行结果

### 4.1 API 测试（CHANGE_API_001 ~ CHANGE_API_012）

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|--------|------|------|
| CHANGE_API_001 | 验证变更分析列表查询API | passed | — |
| CHANGE_API_002 | 验证变更分析列表搜索功能 | passed | — |
| CHANGE_API_003 | 验证变更分析列表分页 | passed | — |
| CHANGE_API_004 | 验证单条变更分析详情API | passed | — |
| CHANGE_API_005 | 验证变更分析详情-changed_files结构 | passed | — |
| CHANGE_API_006 | 验证变更分析详情-无变更文件 | passed | — |
| CHANGE_API_007 | 验证变更分析详情-不存在的ID | passed | — |
| CHANGE_API_008 | 验证分析进度查询-API running | passed | — |
| CHANGE_API_009 | 验证分析进度查询-API pending | passed | — |
| CHANGE_API_010 | 验证分析进度查询-API completed | passed | — |
| CHANGE_API_011 | 验证分析进度查询-API failed | passed | — |
| CHANGE_API_012 | 验证变更分析列表API-未授权访问 | passed | — |

### 4.2 手动功能验证（CHANGE_UI_001 ~ CHANGE_UI_028）

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|--------|------|------|
| CHANGE_UI_001 | 验证变更分析页面默认加载左侧列表 | passed | — |
| CHANGE_UI_002 | 验证变更分析左侧列表loading状态 | passed | — |
| CHANGE_UI_003 | 验证变更分析左侧列表搜索-防抖 | passed | — |
| CHANGE_UI_004 | 验证点击左侧列表项选中高亮 | passed | — |
| CHANGE_UI_005 | 验证选中分析记录后加载详情 | passed | — |
| CHANGE_UI_006 | 验证详情面板-基本信息展示 | passed | — |
| CHANGE_UI_007 | 验证详情面板-提交哈希显示格式 | passed | — |
| CHANGE_UI_008 | 验证详情面板-时间格式化 | passed | — |
| CHANGE_UI_009 | 验证变更文件折叠列表-展开 | passed | — |
| CHANGE_UI_010 | 验证变更文件折叠列表-收起 | passed | — |
| CHANGE_UI_011 | 验证变更文件折叠列表-多项折叠 | passed | — |
| CHANGE_UI_012 | 验证变更类型标签颜色-added | passed | — |
| CHANGE_UI_013 | 验证变更类型标签颜色-modified | passed | — |
| CHANGE_UI_014 | 验证变更类型标签颜色-deleted | passed | — |
| CHANGE_UI_015 | 验证运行中状态进度轮询 | passed | — |
| CHANGE_UI_016 | 验证等待中状态进度显示 | passed | — |
| CHANGE_UI_017 | 验证分析完成时自动刷新列表 | passed | — |
| CHANGE_UI_018 | 验证分析失败时停止轮询 | passed | — |
| CHANGE_UI_019 | 验证未选中记录时详情为空 | passed | — |
| CHANGE_UI_020 | 验证切换记录时停止旧轮询 | passed | — |
| CHANGE_UI_021 | 验证左侧列表空状态 | passed | — |
| CHANGE_UI_022 | 验证左侧列表分页 | passed | — |
| CHANGE_UI_023 | 验证状态标签completed显示 | passed | — |
| CHANGE_UI_024 | 验证状态标签failed显示 | passed | — |
| CHANGE_UI_025 | 验证状态标签running显示 | passed | — |
| CHANGE_UI_026 | 验证状态标签pending显示 | passed | — |
| CHANGE_UI_027 | 验证详情加载失败错误提示 | passed | — |
| CHANGE_UI_028 | 验证详情加载超时处理 | passed | — |

### 4.3 E2E 测试（CHANGE_E2E_001 ~ CHANGE_E2E_003）

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|--------|------|------|
| CHANGE_E2E_001 | 端到端查看变更分析详情流程 | passed | — |
| CHANGE_E2E_002 | 端到端running状态进度跟踪 | passed | — |
| CHANGE_E2E_003 | 端到端切换分析记录流程 | passed | — |

### 4.4 异常场景测试（CHANGE_ERR_001 ~ CHANGE_ERR_005）

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|--------|------|------|
| CHANGE_ERR_001 | 验证列表加载网络失败 | passed | — |
| CHANGE_ERR_002 | 验证详情加载网络失败 | passed | — |
| CHANGE_ERR_003 | 验证进度轮询连续网络抖动 | passed | — |
| CHANGE_ERR_004 | 验证切换记录时旧轮询令牌失效 | passed | — |
| CHANGE_ERR_005 | 验证页面卸载时清理轮询定时器 | passed | — |

---

## 五、执行命令参考

```bash
# 进入前端目录
cd frontend

# 安装依赖（如尚未安装）
npm ci

# 全量执行 ChangeAnalyses 测试
npx playwright test e2e/precision-testing/change-analyses.spec.ts --project=chromium

# 单独执行某一条用例
npx playwright test e2e/precision-testing/change-analyses.spec.ts --project=chromium --grep "CHANGE_API_001"

# 带报告输出
npx playwright test e2e/precision-testing/change-analyses.spec.ts --project=chromium --reporter=html
```

---

## 六、相关文件索引

| 文件 | 路径 |
|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/CHANGE_ANALYSES_TEST_CASES.md` |
| E2E 测试脚本 | `frontend/e2e/precision-testing/change-analyses.spec.ts` |
| JWT 预生成脚本 | `backend/generate_test_token.py` |
| 认证 Fixture | `frontend/e2e/precision-testing/auth-api.ts` |
| API 层封装 | `frontend/src/api/precision-testing.js` |
| 测试计划 | `tests/testcase/precision_testing/Week 5/TEST_PLAN.md` |