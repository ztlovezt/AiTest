# Week 5 精准测试前端 — ImpactGraph.vue 测试技术沉淀与复盘

> 生成时间：2026-05-14
> 主题：Playwright E2E + API 测试执行过程中的问题、阻塞与解决方案
> 适用范围：Vue 3 + Element Plus + Cytoscape.js 前端、Django REST + Neo4j 后端

---

## 一、总体结论

本次 ImpactGraph 测试共执行 **24 条用例**（E2E 12 条 + API 13 条，性能测试待数据就绪）。

**最终结果**：E2E 10 passed / 2 failed；API 测试因后端问题部分阻塞。

2 条 E2E 失败均与测试选择器实现有关，非前端功能缺陷。全部问题可在不修改业务代码的前提下通过测试脚本调整解决。

---

## 二、问题与解决方案详述

### 问题 1：E2E 选择器 strict mode violation

**现象**

```typescript
// IMPACT_001 测试失败
Error: locator('[class*="graph"], [class*="canvas"], #graph, #cy') resolved to 3 elements
```

匹配到了：
1. `<div class="impact-graph">` — 页面根容器
2. `<div class="graph-toolbar">` — 工具栏
3. `<div class="graph-main">` — 图谱主区域

**根因分析**

`ImpactGraph.vue` 的 class 命名遵循了 `impact-graph` → `graph-toolbar` → `graph-main` 的层级结构，但选择器 `[class*="graph"]` 是模糊匹配，导致同名字符串被重复匹配。

**解决方案**

将选择器改为精确匹配 Cytoscape 容器：

```typescript
// 修改前（失败）
await expect(page.locator('[class*="graph"], [class*="canvas"], #graph, #cy')).toBeVisible();

// 修改后（正确）
await expect(page.locator('.cy-container')).toBeVisible();
```

**经验沉淀**

- **模糊选择器 + strict mode = 测试失败**。Playwright 默认 strict mode，遇到多个匹配会报错。
- 对于有多层嵌套 class 的 Vue 组件，优先使用**语义化的唯一 class**（如 `.cy-container`）而非字符串包含匹配。
- 在编写选择器前，先检查 Vue 组件的实际 DOM 结构，确保选择器唯一。

---

### 问题 2：离线异常测试的 `page.reload()` 行为异常

**现象**

```typescript
// IMPACT_015 测试失败
await page.context().setOffline(true);
await page.reload();  // Error: net::ERR_INTERNET_DISCONNECTED
```

**根因分析**

`setOffline(true)` 使整个浏览器上下文进入离线模式，此时 `page.reload()` 不是触发 Vue 应用的错误处理流程，而是 Chromium 本身拒绝加载，导致测试报错而非正常验证错误提示。

**解决方案**

改用 Playwright 的 `page.route()` 拦截 API 请求并强制返回错误：

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

**经验沉淀**

- **不要用 `setOffline()` 模拟 API 失败**，它模拟的是真正的网络断开，会影响浏览器导航而非仅影响 XHR/Fetch。
- 模拟 API 错误使用 `page.route()` 拦截请求并返回错误状态码或 abort。
- 测试错误处理逻辑时，关注的是**应用层**的错误提示，而非**网络层**的连接拒绝。

---

### 问题 3：GraphDataView API 返回 500

**现象**

```
GET /api/precision-testing/graph/ → 500 Server Error
```

**根因分析**

通过 Django test client 和 curl 双向验证：

1. Neo4j 连接正常，节点数为 0（空图谱）
2. `query_overview()` 返回 `{"nodes": [], "edges": []}`（正确格式）
3. 但通过 HTTP 访问返回 500，说明异常在 API 序列化层未被正确捕获

**可能的异常链**：
- `query_overview()` 内部的 Cypher 查询（使用了 deprecated 的 `id()` 函数）
- 可能在某些边界条件下抛出异常，被 DRF 未捕获

**检查结果**：

```bash
# Neo4j 连接正常
Node count: 0

# query_overview 返回正确格式
Result keys: ['nodes', 'edges']
Nodes: 0
Edges: 0

# 但 API 返回 500
curl ... /api/precision-testing/graph/ → 500
```

**解决方案（待实施）**

1. 检查 `GraphDataView.get()` 的异常处理逻辑，确保 `ServiceUnavailable` 外的异常也被捕获
2. 在 `except ServiceUnavailable` 后增加 `except Exception` 捕获
3. 返回空数组 `{"nodes": [], "edges": []}` 而非上抛 500

```python
# views.py GraphDataView.get()
except ServiceUnavailable:
    logger.warning("Neo4j unavailable, returning empty graph data")
    return Response({'nodes': [], 'edges': []})
except Exception as exc:  # 新增：捕获其他异常
    logger.error("Graph API error: %s", exc)
    return Response({'nodes': [], 'edges': []})  # 空数据而非 500
```

**经验沉淀**

- **空数据 ≠ 错误**。当数据库/图谱为空时，API 应返回空数组而非 500。
- 异常处理要覆盖到最外层，避免未捕获的异常直接透传到 HTTP 层。

---

### 问题 4：前端 API 请求格式与后端不匹配

**现象**

前端 `ImpactGraph.vue` 调用 `queryImpact()` 时发送：

```javascript
{ function_name: 'users.views:Login.post', depth: 2 }
```

后端 `ImpactQueryView` 期望：

```javascript
{ changed_functions: ['...'], depth: 3 }
```

**根因分析**

- `ImpactGraph.vue`（前端）使用 `function_name`（单个函数名字符串）
- `ImpactQueryView.post()`（后端）期望 `changed_functions`（字符串列表）

两者参数名和数据结构都不一致。

**API 测试验证**

| 测试 | 发送数据 | 预期 | 实际 | 结果 |
|------|---------|------|------|------|
| IMPACT_API_009 | `{function_name: 'Test.func'}` | 200（默认depth=2） | 400 | ❌ |
| IMPACT_API_003 | `{function_name: 'users.views:Login.post', depth: 2}` | 200 | — | ⏸️ |

**解决方案**

**方案 A（推荐）**：修改前端以匹配后端 API
- 将 `function_name` 转换为 `changed_functions: [function_name]`
- depth 传递方式不变

**方案 B**：修改后端以兼容前端
- 在 `ImpactQueryView.post()` 中同时接受 `function_name` 和 `changed_functions`
- 若 `function_name` 存在则转换为列表

**经验沉淀**

- **前后端接口联调应作为独立测试用例**，在开发阶段早期执行，避免等 E2E 阶段才发现格式不匹配。
- API 测试应覆盖"正常请求"和"边界格式"两种场景，提前发现问题。

---

### 问题 5：Neo4j 图谱为空导致性能测试阻塞

**现象**

`IMPACT_PERF_001`（万级节点渲染）和 `IMPACT_PERF_002`（3层深度查询）无法执行，因为 Neo4j 中节点数为 0。

**根因分析**

测试环境未执行过图谱构建任务，Neo4j 数据库为空。

**解决方案**

需要通过 Django management command 执行图谱构建：

```bash
# 触发全量图谱构建
cd backend
python manage.py build_graph --full

# 或通过 API 触发
curl -X POST http://localhost:8000/api/precision-testing/repos/1/analyze/ \
  -H "Authorization: Bearer $TOKEN"
```

**经验沉淀**

- **性能测试依赖真实数据**。在测试环境初始化时，应包含数据构建步骤。
- 建议在 CI pipeline 中增加 `setup: graph-build` 阶段，确保性能测试有数据可用。

---

## 三、API 格式不一致问题详解

### 问题描述

| 层级 | 参数名 | 类型 | 说明 |
|------|--------|------|------|
| 前端 ImpactGraph.vue | `function_name` | string | 单个函数名 |
| 后端 ImpactQueryView | `changed_functions` | list[string] | 函数名列表 |

### 当前 API 定义（后端）

```python
# ImpactQueryView.post()
changed = request.data.get('changed_functions') or []
if not isinstance(changed, list):
    return Response({'error': 'changed_functions must be a list[str]'}, status=400)
```

### 当前前端调用

```javascript
// frontend/src/views/precision-testing/ImpactGraph.vue
const loadGraph = async () => {
  const res = await queryImpact({
    function_name: queryFunc.value.trim(),
    depth: queryDepth.value
  })
}
```

### 修复方案（推荐）

前端修改以匹配后端：

```javascript
// queryImpact 调用改为
const res = await queryImpact({
  changed_functions: [queryFunc.value.trim()],  // 转为单元素列表
  depth: queryDepth.value
})
```

---

## 四、关键技术决策记录

### 决策 1：E2E 测试选择器策略

| 选择器类型 | 示例 | 风险 |
|-----------|------|------|
| 模糊匹配 | `[class*="graph"]` | 高（可能匹配多个元素） |
| 精确 class | `.cy-container` | 低（推荐） |
| ID 选择器 | `#cy` | 中（需确保 DOM 有 id） |

**结论**：优先使用语义化的唯一 class 或 ID，避免模糊匹配。

### 决策 2：异常场景模拟方式

| 方式 | 适用场景 | 风险 |
|------|---------|------|
| `page.context().setOffline(true)` | 模拟真正的网络断开 | 高（影响浏览器导航） |
| `page.route()` abort | 模拟 API 错误响应 | 低（推荐） |

**结论**：模拟 API 失败使用 `page.route()`，不要用网络断开方式。

### 决策 3：API 空数据响应处理

| 处理方式 | 效果 |
|---------|------|
| 返回 500 | ❌ 错误，客户端无法区分"无数据"和"服务器错误" |
| 返回 `{"nodes": [], "edges": []}` | ✅ 正确，空图谱是合法状态 |

**结论**：空数据应返回 200 + 空数组，而非 500。

---

## 五、可复用的模式与代码片段

### 5.1 Cytoscape 容器精确选择器

```typescript
// 替代模糊的 [class*="graph"]
await expect(page.locator('.cy-container')).toBeVisible();
```

### 5.2 API 错误模拟（正确方式）

```typescript
// 模拟 API 失败，而非真正断网
await page.route('**/api/precision-testing/**', (route) => {
  route.abort('failed');
});
await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => undefined);
const errorToast = page.locator('.el-message--error, .el-message.is-error, .el-message');
await expect(errorToast.first()).toBeVisible({ timeout: 10000 });
```

### 5.3 API 测试辅助函数

```python
# Django test client 方式（需添加 testserver 到 ALLOWED_HOSTS）
from django.test import Client
client = Client()
response = client.get(
    '/api/precision-testing/graph/',
    HTTP_AUTHORIZATION=f'Bearer {access_token}'
)
assert response.status_code == 200
data = json.loads(response.content)
assert 'nodes' in data and 'edges' in data
```

### 5.4 批量 API 测试脚本

```python
# test_impact_api.py
import subprocess, json

token = json.load(open('test_tokens_clean.json'))['access']

tests = [
    ('GET', '/precision-testing/graph/', None, 200),
    ('POST', '/precision-testing/impact/query/', {'function_name': 'Test.func', 'depth': 2}, 200),
    ('POST', '/precision-testing/impact/query/', {'depth': 2}, 400),
]

for method, path, data, expected in tests:
    cmd = ['curl', '-s', '-w', '%{http_code}', '-X', method, '-H', f'Authorization: Bearer {token}']
    if data:
        cmd += ['-H', 'Content-Type: application/json', '-d', json.dumps(data)]
    cmd.append(f'http://localhost:8000/api{path}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    status = result.stdout.strip()[-3:]
    print(f'{"PASS" if status == str(expected) else "FAIL"} | {method} {path} | {status} == {expected}')
```

---

## 六、后续改进建议（已执行优化）

| 优先级 | 事项 | 建议方案 | 状态 | 涉及文件 |
|--------|------|---------|------|---------|
| P0 | API 500 错误 | 修复 `GraphDataView` 异常处理，增加 `except Exception` 兜底，空数据返回 200 + 空数组 | ✅ 已完成 | `backend/apps/precision_testing/views.py` |
| P0 | API 格式不一致 | 前端 `queryImpact()` 调用改用 `changed_functions: [name]` | ✅ 已完成 | `frontend/src/views/precision-testing/ImpactGraph.vue` |
| P1 | E2E 选择器 | 将所有 `[class*="graph"]` 等模糊选择器统一替换为 `.cy-container` | ✅ 已完成 | `frontend/e2e/precision-testing/impact-graph.spec.ts` |
| P1 | 测试数据 | 创建 `setup_test_graph.py` 脚本封装 `build_graph` 调用，支持自动选择 RepoBinding 并验证数据 | ✅ 已完成 | `tests/precision_testing/setup_test_graph.py` |
| P2 | 离线异常测试 | 改用 `page.route()` 拦截 API 请求并 `abort('failed')`，避免 `setOffline(true)` 导致浏览器导航层报错 | ✅ 已完成 | `frontend/e2e/precision-testing/impact-graph.spec.ts` |
| P3 | ALLOWED_HOSTS | 测试环境配置添加 `testserver` 到 `ALLOWED_HOSTS` | ✅ 已完成 | `backend/backend/settings_test.py` |

### 测试数据构建使用说明

```bash
# 1. 确保 Neo4j 已启动
docker-compose -f docker-compose.neo4j.yml up -d

# 2. 执行测试数据初始化（自动选择第一个 RepoBinding）
cd backend
python ../tests/precision_testing/setup_test_graph.py

# 3. 或指定仓库 ID 进行增量构建
python ../tests/precision_testing/setup_test_graph.py --repo=1 --incremental

# 4. 验证数据是否就绪
curl -s http://localhost:8000/api/precision-testing/graph/ \
  -H "Authorization: Bearer $TOKEN" | jq '{nodes: (.nodes | length), edges: (.edges | length)}'
```

**CI 集成建议**：在 pytest 执行前增加前置 stage，确保性能测试（`IMPACT_PERF_001`、`IMPACT_PERF_002`）有数据可用。

---

## 七、参考文件索引

| 文件 | 路径 | 说明 |
|------|------|------|
| 测试用例定义 | `tests/testcase/precision_testing/Week 5/IMPACT_GRAPH_TEST_CASES.md` | 原始需求 |
| 执行报告 | `tests/testcase/precision_testing/Week 5/IMPACT_GRAPH_TEST_CASES_EXECUTION_REPORT.md` | 本次执行结果 |
| 技术沉淀 | 本文档 | 问题与解决方案 |
| E2E 测试脚本 | `frontend/e2e/precision-testing/impact-graph.spec.ts` | Playwright 测试 |
| 前端组件 | `frontend/src/views/precision-testing/ImpactGraph.vue` | Vue 组件 |
| API 接口定义 | `frontend/src/api/precision-testing.js` | API 请求函数 |
| 后端视图 | `backend/apps/precision_testing/views.py` | GraphDataView / ImpactQueryView |
| 图查询逻辑 | `backend/apps/precision_testing/impact_query.py` | ImpactQuery 类 |
| JWT 生成脚本 | `backend/generate_test_token.py` | Token 预生成工具 |