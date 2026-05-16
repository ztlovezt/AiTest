# Week 3 测试用例规格 — Neo4j 图谱构建 + Cypher 影响查询

> 对应模块: `graph_builder.py` / `impact_query.py`
> 生成日期: 2026-05-09
> 评审结论: 通过（评分 94/100）
> 覆盖目标: >= 80%

---

## 测试目录结构

```
tests/testcase/precision_testing/week3/
├── test_graph_builder.py       # GraphBuilder — 全量/增量图谱构建
├── test_impact_query.py        # ImpactQuery — Cypher 影响传播查询
├── test_views.py               # GraphDataView + ImpactQueryView API
└── README.md                    # 本文件
```

---

## 测试覆盖率汇总

| 模块 | 测试用例数 | 覆盖率目标 |
|------|-----------|-----------|
| `graph_builder.py` | 57 | 80%+ |
| `impact_query.py` | 36 | 80%+ |
| API 视图 | 15 | — |
| Neo4j 客户端 | 7 | — |
| 数据库/安全 | 4 | — |
| **合计** | **119** | — |

---

## Week 3 关键交付物路径

- `backend/apps/precision_testing/graph_builder.py`（493 行）— 全量/增量图谱构建
- `backend/apps/precision_testing/impact_query.py`（343 行）— 4 大 Cypher 查询 + ImpactResult
- `backend/apps/precision_testing/views.py`（370 行）— GraphDataView 重写 + ImpactQueryView 新增
- `backend/apps/precision_testing/urls.py`（26 行）— `impact/query/` 路由注册
- `backend/apps/precision_testing/management/commands/verify_graph.py`（203 行）— 图谱校验 CLI

---

## 执行命令

```bash
cd tests
pytest testcase/precision_testing/week3/ -v --tb=short
```

---

## 场景类型覆盖率

| 场景类型 | 覆盖情况 |
|----------|---------|
| 正常（Positive） | ✅ 所有模块 |
| 边界（Boundary） | ✅ depth 边界/空列表/最大分片 |
| 异常（Anomaly） | ✅ Neo4j 不可用/文件不存在/空输入 |
| 组合（Combination） | ✅ E2E 全链路测试 |
| 性能（Performance） | ✅ 增量同步<30s/影响查询<500ms |
| 安全（Security） | ✅ 权限校验/API 输入校验 |