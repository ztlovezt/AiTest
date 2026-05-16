# testhub-platform 接口自动化执行总计划

**编制依据**:`scripts/testhub_api_swagger2.json`(Swagger 2.0,393 路径 / 670 操作 / 22 模块)
**编制日期**:2026-05-06
**当前进度**:1 期已完成(auth/users/projects 39 接口 / 64 用例)
**剩余工作**:19 模块 / 631 操作 / 预估 ≈680 用例

---

## 1. 总体策略

### 1.1 分批原则

按"业务依赖链"分批,每批可独立运行,不跨批次锁同步:

```
auth/users/projects   ← 已完成(基础)
  ↓
testcases / executions / reviews   ← 第 2 批(测试管理三件套,本次主推)
  ↓
api-testing / ui-automation / app-automation   ← 第 3 批(自动化执行)
  ↓
requirement-analysis / ai-testing / agent / assistant / ocr   ← 第 4 批(AI 智能)
  ↓
knowledge-base / reports / scheduler / data-factory / ops-tools / meta-projects / versions / core   ← 第 5 批(辅助)
```

### 1.2 用例颗粒度

| 接口类别 | 推荐用例数 | 必备六维场景 |
|---------|------------|--------------|
| 列表 GET(含分页/过滤/搜索) | 4-5 | Positive + Boundary(分页) + Anomaly(匿名/非法 query) |
| 创建 POST | 4-6 | Positive + Boundary(字段长度) + Anomaly(必填缺失/类型错) + Security(注入) |
| 详情 GET id | 3 | Positive + Anomaly(404/匿名) |
| 全量更新 PUT | 3-4 | Positive + Anomaly(必填缺失/不存在) |
| 部分更新 PATCH | 3 | Positive + Anomaly(只读字段/不存在) |
| 删除 DELETE | 3 | Positive + Anomaly(不存在/级联前置) |
| 业务动作 custom | 3-5 | Positive + Anomaly(状态机违规) + Combination(链路) |

### 1.3 标记体系(沿用第 1 批)

- 优先级:`smoke / p0 / p1 / p2`
- 场景:`positive / boundary / anomaly / combination / security / performance`
- 模块:`testcases / executions / reviews / api_testing / ui_automation / app_automation / ...`
- 评审:`review_required`(LOW 置信度)

---

## 2. 全量模块清单(670 操作)

| 序 | 批次 | 模块 | 操作数 | 路径数 | 估算用例 | 状态 |
|---|------|------|--------|--------|----------|------|
| 1 | 1 | auth | 13 | 9 | 39 | ✅ DONE |
| 2 | 1 | projects | 13 | 8 | 19 | ✅ DONE |
| 3 | 1 | users | 13 | 9 | 6 | ✅ DONE |
| 4 | **2** | **testcases** | **9** | **5** | **30** | 📌 NEXT |
| 5 | **2** | **executions** | **23** | **11** | **65** | 📌 NEXT |
| 6 | **2** | **reviews** | **21** | **9** | **55** | 📌 NEXT |
| 7 | 3 | api-testing | 89 | 49 | 175 | TODO |
| 8 | 3 | ui-automation | 106 | 58 | 200 | TODO |
| 9 | 3 | app-automation | 103 | 63 | 195 | TODO |
| 10 | 4 | requirement-analysis | 71 | 51 | 100 | TODO |
| 11 | 4 | ai-testing | 25 | 13 | 40 | TODO |
| 12 | 4 | agent | 18 | 10 | 30 | TODO |
| 13 | 4 | assistant | 16 | 8 | 25 | TODO |
| 14 | 4 | ocr | 16 | 12 | 25 | TODO |
| 15 | 5 | knowledge-base | 36 | 20 | 60 | TODO |
| 16 | 5 | reports | 13 | 9 | 25 | TODO |
| 17 | 5 | scheduler | 15 | 11 | 25 | TODO |
| 18 | 5 | data-factory | 12 | 8 | 20 | TODO |
| 19 | 5 | ops-tools | 21 | 13 | 35 | TODO |
| 20 | 5 | meta-projects | 12 | 4 | 20 | TODO |
| 21 | 5 | versions | 7 | 3 | 12 | TODO |
| 22 | 5 | core | 18 | 10 | 30 | TODO |
| | | **合计** | **670** | **393** | **≈1230** | |

---

## 3. 第 2 批详细执行计划(本次产出)

### 3.1 模块 testcases(9 ops → 30 用例)

| 接口 | 业务含义 | 用例数 |
|------|---------|--------|
| `GET /api/testcases/` | 测试用例列表 | 5 |
| `POST /api/testcases/` | 创建测试用例 | 6 |
| `GET /api/testcases/{id}/` | 详情 | 3 |
| `PUT /api/testcases/{id}/` | 全量更新 | 3 |
| `PATCH /api/testcases/{id}/` | 部分更新 | 3 |
| `DELETE /api/testcases/{id}/` | 删除 | 3 |
| `GET /api/testcases/import/records/` | 导入记录列表 | 3 |
| `GET /api/testcases/import/template/` | 导入模板下载 | 2 |
| `POST /api/testcases/import/upload/` | 导入上传 | 2 |

**关键依赖**:`created_project`(已存在 fixture)
**新增 fixture**:`created_testcase`、`testcase_payload`

### 3.2 模块 executions(23 ops → 65 用例)

接口集中在三类资源:

| 资源 | 接口数 | 用例 |
|------|--------|------|
| `executions/plans/`(测试计划) | 6 | 18 |
| `executions/runs/`(测试执行) | 5 | 17 |
| `executions/run_cases/`(执行用例项) | 7 | 20 |
| `executions/history/`(历史记录,只读) | 2 | 5 |
| `executions/run_cases/{id}/update_status/` | 1 | 3 |
| `executions/plans/testcases_by_projects/` | 1 | 2 |

**关键依赖**:`created_testcase` + `created_project` + `registered_user`(reviewers)
**新增 fixture**:`created_test_plan`、`created_test_run`

### 3.3 模块 reviews(21 ops → 55 用例)

| 资源 | 接口数 | 用例 |
|------|--------|------|
| `reviews/review-templates/`(模板) | 6 | 15 |
| `reviews/reviews/`(评审实例) | 6 | 18 |
| `reviews/review-comments/`(评论) | 6 | 12 |
| `reviews/reviews/{id}/assign_reviewers/` | 1 | 3 |
| `reviews/reviews/{id}/submit_review/` | 1 | 4 |
| `reviews/reviews/my_reviews/` | 1 | 3 |

**关键依赖**:`created_testcase` + `created_project` + 多个 `registered_user`
**新增 fixture**:`created_review_template`、`created_review`

---

## 4. 后续批次执行节奏(建议)

| 批次 | 预计耗时 | 依赖 fixture | 关键风险 |
|------|----------|--------------|----------|
| 第 2 批 | 已交付 | testcase / plan / run / review / template | swagger 字段不全,业务规则需对照 view 验证 |
| 第 3 批 | 4-6 工时 | environment / api_case / ui_element / app_package | api-testing 依赖外部 mock,ui/app 依赖驱动启动 |
| 第 4 批 | 3-4 工时 | requirement_doc / model_config / prompt_template | 调用 LLM 计费,需准备 mock 或 dry-run 模式 |
| 第 5 批 | 3-4 工时 | knowledge_doc / data_template / cron_schedule | 多为辅助,可降优先级 |

**总耗时估算**:第 2-5 批合计约 **12-18 工时**实施 + 4-6 工时调优。

---

## 5. 持续运行策略

### 5.1 推荐运行命令(已在 README.md)

```bash
cd tests/api

# 冒烟(每次 CI 必跑,< 30s)
pytest -m smoke

# 第 N 批回归
pytest -m "testcases or executions or reviews"   # 第 2 批
pytest -m "api_testing or ui_automation or app_automation"  # 第 3 批

# 全量(夜间)
pytest -m "not review_required" --html=report.html

# 并行(8 worker)
pytest -n 8 -m "not security"
```

### 5.2 数据隔离与清理

**当前缺陷**:测试创建的 testcase / plan / run 不会清理,会污染开发环境。

**改进方案**(在 conftest.py 添加):

```python
@pytest.fixture(autouse=True, scope="session")
def _cleanup(request):
    yield
    # session 末尾批量删除 qa_* 前缀的项目/用例(管理员账号)
```

### 5.3 限流与重试

- register 接口限流 5 次/min(已在 fixture 加 429 退避)
- 高并发批量跑建议 `pytest -p no:randomly --reruns 1 --reruns-delay 5`
- 第 3-5 批涉及 AI/外部调用的接口建议 `--timeout=60`

---

## 6. 已知风险与待确认项

### 6.1 swagger 字段不全(沿用第 1 批的 LOW 标记策略)

| 模块 | 接口 | 风险 | 处理 |
|------|------|------|------|
| testcases | POST `/import/upload/` | 文件字段未声明 | 用 `multipart/form-data` 实测,LOW |
| executions | POST `/runs/` | TestRun 字段未严格声明 | 对照 `apps/executions/views.py` 验证 |
| reviews | POST `/reviews/` 的 reviewers | 是否要求 user_id 列表 | 对照 view 与 serializer |
| api-testing | 大量 schema | drf-spectacular 在 ViewSet 上未细化 | 进入第 3 批前批量验证 |

### 6.2 跨模块组合用例(第 2 批已规划)

- E2E_001:创建项目 → 创建测试用例 → 创建测试计划 → 创建执行 → 提交结果
- E2E_002:创建评审模板 → 创建评审 → 分配评审人 → 提交评审 → 查询 my_reviews
- E2E_003:批量导入用例 → 校验列表 → 删除导入记录

---

## 7. 交付物清单(本次)

| 文件 | 内容 | 状态 |
|------|------|------|
| `scripts/extract_full_modules.py` | swagger 全模块扫描脚本 | ✅ |
| `scripts/modules_full.json` | 全 670 操作元数据 | ✅ |
| `scripts/modules_summary.json` | 22 模块统计 | ✅ |
| `tests/api/TEST_PLAN.md`(本文件) | 总执行计划 | ✅ |
| `tests/api/testcases_phase2.md` | 第 2 批 150 用例文档 | ✅ |
| `tests/api/conftest.py`(扩展) | 新增 phase2 fixtures | ✅ |
| `tests/api/test_testcases.py` | testcases 模块 pytest | ✅ |
| `tests/api/test_executions.py` | executions 模块 pytest | ✅ |
| `tests/api/test_reviews.py` | reviews 模块 pytest | ✅ |
| `tests/api/pytest.ini`(扩展) | 新增 marker | ✅ |

---

## 8. 第 3-5 批用例设计大纲(后续按需展开)

### 8.1 第 3 批 — 自动化执行(298 ops)

**共性接口模板**:CRUD + run + result + log。每模块按以下骨架设计:

| 类别 | 用例数(单模块) | 关键场景 |
|------|------------------|----------|
| 资源 CRUD(case/suite/element) | 30-50 | 标准 CRUD 六维 |
| 触发执行 POST `/run/` | 5-8 | 同步触发/异步触发/排队/超时 |
| 结果查询 GET `/result/{id}/` | 4-5 | 通过/失败/进行中/不存在 |
| 日志查询 GET `/log/` | 3 | 分页/筛选/匿名 |
| 文件上传(脚本/图片) | 3-5 | 大小限制/类型校验/损坏 |

### 8.2 第 4 批 — AI 智能(146 ops)

**特殊点**:涉及 LLM 调用,务必加 mock。

| 模块 | 关键场景 |
|------|----------|
| requirement-analysis | 文档上传 → AI 拆分 → 用例生成(组合) |
| ai-testing | 模型配置 CRUD / Prompt 模板 / 评测任务 |
| agent | 智能体调用 / 工具列表 / 会话管理 |
| assistant | 对话流式 / 上下文截断 / 函数调用 |
| ocr | 图片识别 / PDF 解析 / 错误重试 |

### 8.3 第 5 批 — 辅助(134 ops)

按"基础查询 + 标准 CRUD"快速覆盖,场景以 Positive + Anomaly 为主。

---

## 9. 完成定义(DoD)

- ✅ 每个待测接口至少 1 个 Positive + 1 个 Anomaly 用例
- ✅ 所有用例可通过 `pytest -m {module}` 独立运行
- ✅ 用例代码与 Markdown 文档 ID 1:1 对应
- ✅ HTML 报告通过率 ≥ 90%(剩余 10% 应为已识别的 LOW/review_required 或真实 bug)
- ✅ EXECUTION_REPORT.md 记录每批执行结论与 bug 清单
