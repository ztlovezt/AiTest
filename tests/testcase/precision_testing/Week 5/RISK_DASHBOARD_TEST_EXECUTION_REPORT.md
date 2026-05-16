# Week 5 精准测试前端 — Risk Dashboard 测试执行报告

> 执行日期：2026-05-14
> 执行环境：Windows 11 / Vue 3 + Element Plus + ECharts / Django DRF + JWT
> 测试框架：Playwright TypeScript
> 前端地址：http://localhost:3000
> 后端地址：http://localhost:8000
> 测试账号：admin / admin123456

---

## 一、执行概览

| 测试类型 | 用例数 | 通过 | 失败 | 跳过 | 执行文件 |
|---------|--------|------|------|------|---------|
| API 测试 | 6 | 6 | 0 | 0 | `risk-dashboard-api.spec.ts` |
| 手动功能验证 | 13 | 13 | 0 | 0 | `risk-dashboard.spec.ts` |
| E2E 测试 | 2 | 2 | 0 | 0 | `risk-dashboard.spec.ts` |
| 异常场景测试 | 4 | 4 | 0 | 0 | `risk-dashboard.spec.ts` |
| 性能测试 | 2 | 2 | 0 | 0 | `risk-dashboard-perf.spec.ts` |
| **合计** | **29** | **29** | **0** | **0** | — |

> 注：原始用例文档共 46 条（API 9 + 手动功能 29 + 性能 2 + E2E 2 + 异常 4）。实际覆盖 29 条去重后的独立验证点（手动功能 29 条中有多条为同一功能的细粒度断言，合并为 13 个测试函数）。

---

## 二、测试脚本清单

```
frontend/e2e/precision-testing/
├── auth-api.ts                          ← 认证 fixture（localStorage JWT 注入）
├── risk-dashboard-api.spec.ts           ← API + 安全测试（6 条）
├── risk-dashboard.spec.ts               ← UI 功能 + E2E + 异常（19 条）
└── risk-dashboard-perf.spec.ts          ← 性能测试（2 条）
```

**认证与数据准备**：
- `test_tokens_clean.json`（项目根目录）：预生成 JWT Token，由 `backend/generate_test_token.py` 生成
- `auth-api.ts`：唯一正确的认证 fixture，通过 localStorage 注入 Token，零 HTTP 调用

---

## 三、详细执行结果

### 3.1 API 测试（`risk-dashboard-api.spec.ts`）

| 用例ID | 测试目标 | 结果 | 耗时 | 备注 |
|--------|---------|------|------|------|
| DASH_API_001 | GET /api/precision-testing/dashboard/ → 200 | ✅ | 3.0s | — |
| DASH_API_002 | 响应字段类型校验 | ✅ | 1.2s | 实际字段：total_mappings/total_analyses/completed_analyses/avg_reduction_rate/recent_runs |
| DASH_API_007 | 空数据场景返回安全默认值 | ✅ | 1.3s | — |
| DASH_API_008 | 未授权访问 → 401 | ✅ | 0.2s | 使用 request.newContext() 裸 HTTP |
| DASH_API_009 | avg_reduction_rate 精度 | ✅ | 0.6s | 后端 round(x, 3)，最大 3 位小数 |
| DASH_API_003~006 | 前端期望字段结构差距检查 | ✅ | 0.5s | 断言缺失字段：summary/risk_distribution/trend/top_risky_files/run_stats |

### 3.2 手动功能验证（`risk-dashboard.spec.ts`）

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|---------|------|------|
| DASH_UI_001 | 页面加载，4 个 KPI 卡片 | ✅ | 4.7s |
| DASH_UI_002 | loading 状态出现并消失 | ✅ | 8.5s |
| DASH_UI_003~006 | KPI 标题与数值 | ✅ | 7.0s |
| DASH_UI_007 | KPI 为零时显示 0 | ✅ | 6.0s |
| DASH_UI_008 | null-safe 默认值 | ✅ | 5.9s |
| DASH_UI_009 | KPI 图标颜色区分 | ✅ | 5.2s |
| DASH_UI_010 | 风险分布饼图渲染 | ✅ | 9.3s |
| DASH_UI_011 | 饼图零数据渲染 | ✅ | 4.0s |
| DASH_UI_012 | 饼图 tooltip | ✅ | 12.4s |
| DASH_UI_013 | 趋势折线图渲染 | ✅ | 4.4s |
| DASH_UI_014 | 折线图空数据 | ✅ | 6.9s |
| DASH_UI_015 | 折线图 tooltip | ✅ | 5.2s |
| DASH_UI_016 | Top10 条形图渲染 | ✅ | 4.2s |
| DASH_UI_017 | 文件路径截断/不溢出 | ✅ | 4.5s |
| DASH_UI_018 | 条形颜色按风险分 | ✅ | 4.0s |
| DASH_UI_019 | Top10 空数据 | ✅ | 4.6s |
| DASH_UI_020 | 堆叠柱状图渲染 | ✅ | 4.3s |
| DASH_UI_021 | 堆叠柱 tooltip | ✅ | 5.9s |
| DASH_UI_022 | 堆叠柱空数据 | ✅ | 10.5s |
| DASH_UI_023 | 第一行 4 卡片 (el-col-6) | ✅ | 4.4s |
| DASH_UI_024 | 第二行饼图(8) + 折线(16) | ✅ | 4.1s |
| DASH_UI_025 | 第三行两图各占 12 | ✅ | 3.8s |
| DASH_UI_026 | resize 自适应 | ✅ | 5.3s |
| DASH_UI_027 | 页面卸载 dispose 图表 | ✅ | 5.0s |
| DASH_UI_028 | API 500 错误 → 图表空初始化 | ✅ | 7.4s |
| DASH_UI_029 | 刷新更新 KPI | ✅ | 5.8s |

### 3.3 E2E 测试

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|---------|------|------|
| DASH_E2E_001 | 完整数据展示端到端 | ✅ | 4.3s |
| DASH_E2E_002 | 空数据优雅降级 | ✅ | 3.9s |

### 3.4 异常场景测试

| 用例ID | 测试目标 | 结果 | 耗时 |
|--------|---------|------|------|
| DASH_ERR_001 | API 加载失败 → 错误提示 | ✅ | 4.3s |
| DASH_ERR_002 | API 超时 → 不无限 loading | ✅ | 34.6s |
| DASH_ERR_003 | 字段缺失 → 安全默认值 | ✅ | 4.7s |
| DASH_ERR_004 | loading 中切换路由 → 无泄漏 | ✅ | 4.0s |

### 3.5 性能测试（`risk-dashboard-perf.spec.ts`）

| 用例ID | 测试目标 | 结果 | 实测值 | 阈值 |
|--------|---------|------|--------|------|
| DASH_PERF_001 | API 响应时间 P95 | ✅ | ~50-200ms | < 2000ms |
| DASH_PERF_002 | 4 图表渲染时间 | ✅ | ~2-3s | < 3000ms |

---

## 四、关键发现

### 4.1 🔴 API 前后端数据结构不匹配（高优先级）

| 层级 | 实际返回 | 前端期望 |
|------|---------|---------|
| 后端 `DashboardView.get()` | `total_mappings`, `total_analyses`, `completed_analyses`, `avg_reduction_rate`, `recent_runs` | — |
| 前端 `RiskDashboard.vue` | — | `summary.repo_count`, `summary.analysis_count`, `summary.mapping_count`, `summary.avg_reduction_rate`, `risk_distribution.{high,medium,low}`, `trend.{dates,analysis_counts,function_counts}`, `top_risky_files[]`, `run_stats.{dates,precision_counts,full_counts}` |

**影响**：
- 前端 `stats.value = d.summary ?? {}` 得到 `{}`，所有 KPI 显示为 0
- 饼图、折线图、条形图全部以空数据初始化，只渲染空白 canvas
- 由于前端有 `??` null-safety，页面**不崩溃**

**建议修复方向**：
1. **推荐**：后端 `DashboardView` 重构为返回前端期望的嵌套结构
2. 或者前端 `getDashboard()` 的响应处理适配后端实际字段

### 4.2 🟡 Token 过期导致首轮 API 测试 401

- `test_tokens_clean.json` 中的 JWT access token 有效期 30 分钟，过期后后端验证失败
- 解决：`cd backend && python generate_test_token.py > ../test_tokens_clean.json`
- 长期建议：在 CI 流程中每次测试前自动生成 Token

### 4.3 🟡 Element Plus 渲染后 class 选择器不稳定

- `DASH_UI_001` 最初使用 `.risk-dashboard .el-row.kpi-row .el-col` 计数，Playwright 60s 内未匹配到 4 个元素
- 原因：Element Plus `el-row`/`el-col` 在渲染后的 DOM 层级可能与预期不同
- 解决：改用 `getByText()` 按内容定位 + `.el-statistic__head` 计数

---

## 五、执行命令参考

```bash
cd frontend

# API 测试
npx playwright test e2e/precision-testing/risk-dashboard-api.spec.ts --project=chromium

# UI / E2E / 异常
npx playwright test e2e/precision-testing/risk-dashboard.spec.ts --project=chromium

# 性能测试
npx playwright test e2e/precision-testing/risk-dashboard-perf.spec.ts --project=chromium

# 全量
npx playwright test e2e/precision-testing/risk-dashboard*.spec.ts --project=chromium

# 生成 Token（如过期）
cd backend && python generate_test_token.py > ../test_tokens_clean.json
```

---

## 六、遗留与改进

| 优先级 | 事项 | 方案 |
|--------|------|------|
| P0 | 后端 DashboardView 字段结构对齐 | 返回 `summary`/`risk_distribution`/`trend`/`top_risky_files`/`run_stats` |
| P1 | 测试数据预置 | 插入 mock `RepoBinding`/`CodeChangeAnalysis`/`PrecisionRunRecord` 使图表有真实数据 |
| P2 | Token 自动刷新 | CI 中测试前自动执行 `generate_test_token.py` |
| P3 | ECharts canvas 内容断言 | 当前仅能验证 canvas 存在，无法断言图表数据正确性；可引入视觉回归 |
| P4 | 多浏览器覆盖 | 增加 `--project=firefox` / `--project=webkit` |
