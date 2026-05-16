# Precision Testing Week 1 测试套件

> **模块**: `apps.precision_testing` — 精准测试基础架构
> **生成日期**: 2026-05-08
> **方法论**: ai-api-testcase-generator 四步工作流（输入理解→场景推断→用例表达→质量验证）

## 文件结构

```
tests/testcase/precision_testing/week1/
├── README.md              # 本文件 — 测试套件说明
├── __init__.py
├── conftest.py            # pytest fixtures（公共测试数据）
├── test_api_week1.py      # 测试用例规范（TC-001 ~ TC-070）
└── test_api_week1_pytest.py # 可执行 pytest 脚本（70 个测试函数）
```

## 运行方式

```bash
# 运行所有 Week 1 测试
pytest tests/testcase/precision_testing/week1/ -v

# 运行指定 TC
pytest tests/testcase/precision_testing/week1/ -v -k "TC-001"

# 生成覆盖率报告
pytest tests/testcase/precision_testing/week1/ --cov=apps.precision_testing --cov-report=term-missing
```

## 测试用例统计

| 场景类型 | TC 数量 | 覆盖端点 |
|---------|--------|---------|
| Positive | 35 | repos, analyses, mappings, impact, predictions, runs, graph, dashboard, webhook, gate, neo4j |
| Boundary | 7 | confidence=0.0, max_length=500, progress=0/100, empty DB, default params |
| Anomaly | 17 | missing fields, invalid values, not found, duplicate constraint |
| Combination | 4 | atomic transaction, multiple status values, 3 mapping types |
| Performance | 2 | N+1 query check, app startup |
| Security | 4 | authentication, authorization, readonly protection |

**总计**: 70 个测试用例，覆盖 19 个 API 端点

## 覆盖率目标

- 语句覆盖率 ≥ 80%
- 分支覆盖率 ≥ 75%
- 关键路径覆盖：100%

## 前置条件

测试需要以下 fixtures（定义在 `conftest.py`）：

| Fixture | 说明 |
|--------|------|
| `api_client` | 未认证 DRF APIClient |
| `authenticated_client` | 已认证用户（JWT）|
| `project` | 现有 Project 实体 |
| `another_project` | 另一个 Project（避免 unique_together 冲突）|
| `sample_repo_binding` | 激活的仓库绑定 |
| `sample_code_change_analysis` | 已完成变更分析 |
| `inactive_repo_binding` | 未激活仓库绑定 |
| `completed_analysis_with_impact` | 完整的影响分析链 |
| `running_analysis` | 运行中分析 |
| `failed_analysis` | 失败分析 |
| `testcase` | 现有 TestCase 实体 |

## 关键测试场景

### P0 必须覆盖

1. **CRUD 操作**: RepoBinding / TestCaseCodeMapping / RiskPredictionRecord / PrecisionRunRecord
2. **异步任务触发**: analyze / auto_build / trigger — 验证 202 Accepted + task_id
3. **进度轮询**: analyses/{id}/progress/ — pending/running/completed/failed 四状态
4. **权限验证**: 认证 vs 未认证
5. **Git Webhook**: 完整 push 事件处理流程
6. **覆盖率门禁**: passed/failed 两种结果
7. **Neo4jClient**: 单例模式、连接验证、批量写入

### 边界条件

- `confidence=0.0` / `confidence=1.5`（FloatField 约束）
- `repo_path` 500 字符 / 501 字符
- `progress` 0 / 100 边界
- 空数据库（返回空列表/零值）
- `avg_reduction_rate=None` 降级

### 降级场景

- Neo4j 连接失败 → `verify_connectivity()` 返回 False，不阻断应用启动
- `PrecisionTestingConfig.ready()` 捕获异常仅记录 warning
- Dashboard 的 `aggregate(Avg('reduction_rate'))` 返回 None 时 → `or 0.0`

## 关联文档

- [精准测试设计策略方案及执行计划.md](../../../../notes/精准测试设计策略方案及执行计划.md)
- [apps/precision_testing/](../../../../../backend/apps/precision_testing/)