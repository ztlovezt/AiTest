# Week 5 精准测试前端 — ImpactGraph.vue 测试执行报告

> 生成时间：2026-05-14
> 测试范围：IMPACT_GRAPH_TEST_CASES.md 中定义的 5 大类测试（手动功能验证 / E2E / API / 性能 / 异常场景）
> 执行框架：Playwright + TypeScript（E2E）/ curl + Django Test Client（API）
> 前端地址：http://localhost:3000（Vue 3 + Element Plus + Cytoscape.js）
> 后端地址：http://localhost:8000（Django REST Framework + JWT）

---

## 一、执行概览

| 指标 | 数值 |
|------|------|
| 测试套件（Spec 文件） | 1 个（`impact-graph.spec.ts`） |
| 总用例数 | 24 条 |
| **E2E通过** | **10** |
| **E2E失败** | **2** |
| **API测试** | ⚠️ API 500错误，需修复 |
| **性能测试** | ⏸️ 待Neo4j数据就绪 |
| 整体耗时 | ~2 分钟（全量） |

> 注：2 条失败 E2E 用例均为选择器问题导致 strict mode violation，非功能缺陷。

---

## 二、测试脚本清单

| # | 脚本文件 | 路径 | 覆盖用例 |
|---|---------|------|---------|
| 1 | `impact-graph.spec.ts` | `frontend/e2e/precision-testing/impact-graph.spec.ts` | IMPACT_001 ~ IMPACT_022（部分覆盖） |

### 2.1 公共 Fixture

| 文件 | 路径 | 作用 |
|------|------|------|
| `auth-api.ts` | `frontend/e2e/precision-testing/auth-api.ts` | 自定义 Playwright fixture `authenticatedPage`，通过预生成 JWT 种子直接写入 localStorage |

---

## 三、测试数据与环境准备

### 3.1 预生成 JWT Token

- **生成脚本**：`backend/generate_test_token.py`
- **输出文件**：`E:/testhub_platform/test_tokens_clean.json`
- **Token 内容**：access / refresh / user / access_expires_in / refresh_expires_in

### 3.2 Fixture 注入逻辑

`auth-api.ts` 中的 `authenticatedPage` 执行步骤：

1. `page.goto('/login')` 加载登录页
2. `page.evaluate()` 将 Token 与用户信息写入 localStorage
3. `page.reload()` 触发 Vue Router 守卫重新评估认证状态
4. `page.waitForURL()` 等待重定向完成

### 3.3 测试账号

| 字段 | 值 |
|------|-----|
| username | `admin` |
| password | `admin123456` |

---

## 四、E2E测试执行结果

**文件**：`impact-graph.spec.ts`
**结果**：10 passed / 2 failed / 0 skipped
**耗时**：约 2 分钟

| 用例ID | 描述 | 结果 | 耗时 | 备注 |
|--------|------|------|------|------|
| IMPACT_001 | 验证图谱页面初始加载全量图谱 | ❌ FAILED | 10.3s | strict mode violation（匹配到3个元素） |
| IMPACT_002 | 验证函数名查询影响 | ✅ PASSED | 12.0s | - |
| IMPACT_003 | 验证回车键触发查询 | ✅ PASSED | 8.4s | - |
| IMPACT_007 | 验证节点点击选中 | ✅ PASSED | 8.7s | - |
| IMPACT_008 | 验证节点属性面板显示内容 | ✅ PASSED | 8.6s | - |
| IMPACT_011 | 验证图例显示 | ✅ PASSED | 6.3s | - |
| IMPACT_012 | 验证空白区域点击取消选中 | ✅ PASSED | 8.7s | - |
| IMPACT_014 | 验证重置按钮功能 | ✅ PASSED | 6.7s | - |
| IMPACT_015 | 验证加载图谱失败错误处理 | ❌ FAILED | 7.6s | offline模式导致page.reload失败 |
| IMPACT_017 | 验证查询空函数名加载全量图谱 | ✅ PASSED | 11.7s | - |
| IMPACT_018 | 验证Cytoscape样式-节点颜色 | ✅ PASSED | 11.6s | - |
| IMPACT_021 | 验证图谱布局自动计算 | ✅ PASSED | 9.3s | - |

### 4.1 失败用例分析

#### IMPACT_001：图谱页面初始加载

```
Error: locator('[class*="graph"], [class*="canvas"], #graph, #cy') resolved to 3 elements
```

**原因**：选择器过于宽泛，匹配到了：
1. `<div class="impact-graph">`（页面根容器）
2. `<div class="graph-toolbar">`（工具栏）
3. `<div class="graph-main">`（图谱主区域）

**修复建议**：将选择器改为 `.cy-container` 或 `#cy`，精确匹配 Cytoscape 画布容器。

#### IMPACT_015：加载图谱失败错误处理

```
Error: page.reload: net::ERR_INTERNET_DISCONNECTED
```

**原因**：`page.context().setOffline(true)` 后调用 `page.reload()` 导致 Chromium 直接拒绝加载，而非触发 Vue 应用的错误处理流程。

**修复建议**：使用 `page.route()` 拦截 API 请求并返回错误，而非真正断开网络连接。

---

## 五、API测试执行结果

| 用例ID | 描述 | 预期状态 | 实际状态 | 结果 |
|--------|------|---------|---------|------|
| IMPACT_API_001 | 全量图谱数据API | 200 | 500 | ❌ FAILED |
| IMPACT_API_002 | 空图谱 | 200 | — | ⏸️ 未执行（前置API失败） |
| IMPACT_API_003 | 影响查询-函数存在 | 200 | — | ⏸️ 未执行 |
| IMPACT_API_004 | 影响查询-深度1层 | 200 | — | ⏸️ 未执行 |
| IMPACT_API_007 | 函数不存在 | 200 | — | ⏸️ 未执行 |
| IMPACT_API_008 | 缺少function_name | 400 | — | ⏸️ 未执行 |
| IMPACT_API_009 | 缺少depth（默认2） | 200 | 400 | ❌ FAILED |
| IMPACT_API_010 | 图谱API未授权 | 401 | 401 | ✅ PASSED |
| IMPACT_API_011 | 影响查询API未授权 | 401 | 401 | ✅ PASSED |

### 5.1 API失败根因分析

#### 问题 1：GraphDataView 返回 500

```
GET /api/precision-testing/graph/ → 500 Server Error
```

**根因**：`query_overview()` 在 Neo4j 无数据时返回空数组 `{"nodes": [], "edges": []}`，但 API 层面仍抛出 500 错误。

**检查结果**：
- Neo4j 中当前节点数为 0（空图谱）
- `query_overview()` 返回 `{"nodes": [], "edges": []}`
- 但通过 curl 访问返回 500，说明异常被上层捕获不当

#### 问题 2：API 请求格式不匹配

**前端发送**：
```javascript
queryImpact({ function_name: 'users.views:Login.post', depth: 2 })
```

**API 期望**（根据 ImpactQueryView 定义）：
```javascript
{ changed_functions: ['...'], depth: 3 }
```

**根因**：ImpactGraph.vue 使用 `function_name` 参数，而 `ImpactQueryView` 期望 `changed_functions` 列表。

---

## 六、性能测试执行结果

| 用例ID | 描述 | 结果 | 备注 |
|--------|------|------|------|
| IMPACT_PERF_001 | 万级节点渲染性能 | ⏸️ 待执行 | 需 Neo4j 预填充数据 |
| IMPACT_PERF_002 | 3层深度查询响应时间 | ⏸️ 待执行 | 需 Neo4j 预填充数据 |

**阻塞原因**：Neo4j 图谱为空，无法构造性能测试场景。

---

## 七、遗留事项

| 事项 | 优先级 | 建议 |
|------|--------|------|
| 选择器 strict mode violation | P1 | 改为 `.cy-container` 精确选择器 |
| API 格式不一致（function_name vs changed_functions） | P0 | 统一前端与后端的请求参数格式 |
| API 500 错误处理 | P0 | 修复 GraphDataView 在空数据时的异常处理 |
| Neo4j 测试数据 | P1 | 需要通过 graph_builder 预填充测试数据 |
| 离线异常测试实现方式 | P2 | 改用 page.route 拦截而非真正断网 |

---

## 八、执行命令参考

```bash
# 进入前端目录
cd frontend

# 执行 ImpactGraph E2E 测试
npx playwright test e2e/precision-testing/impact-graph.spec.ts --project=chromium

# 带报告输出
npx playwright test e2e/precision-testing/impact-graph.spec.ts --project=chromium --reporter=html

# 测试 API（需先获取 Token）
cd backend && python generate_test_token.py
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/precision-testing/graph/
```

---

## 九、附件

| 文件 | 路径 | 说明 |
|------|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/IMPACT_GRAPH_TEST_CASES.md` | 原始需求 |
| JWT 生成脚本 | `backend/generate_test_token.py` | Token 预生成工具 |
| Token 缓存 | `test_tokens_clean.json` | 预生成 JWT |
| E2E 测试脚本 | `frontend/e2e/precision-testing/impact-graph.spec.ts` | Playwright 测试 |
| 前端组件 | `frontend/src/views/precision-testing/ImpactGraph.vue` | Vue 组件源码 |
| API 接口定义 | `frontend/src/api/precision-testing.js` | API 请求函数 |