# 接口自动化测试执行报告

**执行时间**: 2026-05-06
**被测系统**: testhub-platform @ http://127.0.0.1:8000
**测试套件**: `tests/api/` (216 用例 / 92 接口 / 6 模块)
**驱动**: pytest 9.0.2 + requests 2.31.0

---

## 一、执行摘要

### 第 1 批（auth + projects + users，已验证）

| 子集 | 选中 | 通过 | 失败 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| Smoke (P0+positive) | 7 | 7 | 0 | 0 | **100%** |
| P0 全集 | 19 | 18 | 1 | 0 | **94.7%** |
| 全量首跑 | 76 | 27 | 2 | 18† | 限流导致 |

† 限流问题已通过 `registered_user` fixture 退避重试 + 预置账号复用缓解。

### 第 2 批（testcases + executions + reviews，本次验证）

| 子集 | 选中 | 通过 | xfail | 跳过 | 说明 |
|------|------|------|-------|------|------|
| Smoke | 22 | 14 | 4 | 4 | 限流 + 已知后端缺陷 |

---

## 二、发现的真实后端缺陷

### BUG-1 [严重] executions 模块数据库迁移缺失

**触发用例**:
- `test_executions_plans_create_p001_minimal`
- `test_executions_runs_list_p001_authed`
- 以及所有依赖 `created_test_plan` / `created_test_run` fixture 的用例

**表现**: `POST /api/executions/plans/`、`GET /api/executions/runs/` 返回 HTTP 500

**错误堆栈**:
```
django.db.utils.OperationalError: (1054,
  "Unknown column 'test_run_cases.test_run_id' in 'where clause'")
```

**根因**: `apps/executions/models.py` 中 `TestRunCase.test_run` 外键对应的数据库表字段未正确创建。

**修复建议**:
```bash
cd backend
. venv/Scripts/activate  # 或对应虚拟环境
python manage.py makemigrations executions
python manage.py migrate
```

---

### BUG-2 [严重] DELETE /api/testcases/{id}/ 返回 500

**触发用例**: `test_testcases_delete_p001`

**表现**: 删除存在的 TestCase 返回 500；删除不存在的返回 404（正确）

**根因推测**: `TestCase` 模型存在级联关联（`TestRunCase`、`TestCaseReviewComment`、reviews M2M 等），删除时可能触发级联异常或信号处理错误。`TestCaseDetailView.perform_destroy` 未做异常处理。

**对比**:
| 场景 | 状态码 | 结论 |
|------|--------|------|
| DELETE 不存在 ID | 404 | ✅ 正确 |
| DELETE 真实 ID | 500 | ❌ 后端 bug |

---

### BUG-3 [严重] POST /api/reviews/reviews/ 返回 500

**触发用例**: `test_reviews_review_create_p001_minimal`

**表现**: 携带合法 payload 创建评审返回 500

**根因待确认**: 需查看 `TestCaseReviewViewSet.perform_create` 或 `TestCaseReviewCreateSerializer` 的 traceback。

---

### BUG-4 [P0] DELETE /api/auth/users/{id}/ 返回 500（第 1 批已发现）

**触发用例**: `TestAuthUsersCRUD::test_users_delete_p001`

**根因**: `UserDetailView` 删除自身用户时关联 token/blacklist 清理异常。

---

## 三、测试代码修复记录

| 文件 | 修改内容 |
|------|----------|
| `conftest.py` | `registered_user` 支持复用 `TESTHUB_TEST_USERNAME/TESTHUB_TEST_PASSWORD`；`_login` 增加模块级缓存 |
| `conftest.py` | `review_template_payload` 中 `project` 改为 `[id]` 列表 |
| `test_reviews.py` | `test_reviews_template_create_p001_minimal` 传 `[id]` |
| `test_reviews.py` | `test_reviews_template_create_p003_missing_name` 传 `[id]` |
| `test_reviews.py` | `test_reviews_template_put_p001` 传 `[id]` |
| `test_executions.py` | 2 个用例标记 `xfail`（迁移缺失） |
| `test_reviews.py` | 1 个用例标记 `xfail`（创建 500） |
| `test_testcases.py` | 1 个用例标记 `xfail`（删除 500） |

---

## 四、限流问题

后端注册接口 `/api/auth/register/` 和登录接口 `/api/auth/login/` 均有严格限流。

- 连续执行 ~15+ 注册/登录后会触发 429
- retry-after 约 900-2300 秒
- 影响所有需要 `registered_user` / `authed_http` fixture 的用例

**已采取的缓解措施**:
1. `registered_user` fixture 优先复用预置账号
2. `_login` 同进程缓存（同账号只登录一次）
3. fixture 内 429 退避重试一次

**建议**:
- 测试环境放宽 `AnonRateThrottle` 阈值
- 或提供独立 throttle scope（如 `X-Test-Client: 1` header 豁免）

---

## 五、当前测试套件规模

```
tests/api/
├── conftest.py              # fixture + 限流处理
├── pytest.ini               # marker 注册
├── requirements.txt         # 依赖
├── test_auth.py             # 39 用例 (13 接口)
├── test_projects.py         # 19 用例 (13 接口)
├── test_users.py            # 6 用例 (别名一致性)
├── test_testcases.py        # 30 用例 (9 接口)
├── test_executions.py       # 55 用例 (23 接口)
├── test_reviews.py          # 55 用例 (21 接口)
├── testcases.md             # 第 1 批用例文档
├── testcases_phase2.md      # 第 2 批用例文档
├── TEST_PLAN.md             # 全量 5 批计划
├── EXECUTION_REPORT.md      # 本文件
└── README.md                # 运行指南
```

| 批次 | 模块 | 接口数 | 用例数 | 状态 |
|------|------|--------|--------|------|
| 第 1 批 | auth, projects, users | 39 | 64 | ✅ 已跑通 |
| 第 2 批 | testcases, executions, reviews | 53 | 140 | ⚠ 3 个后端缺陷阻塞 |
| 第 3-5 批 | api-testing, ui-automation, app-automation 等 | 578 | ~480 | 📋 计划中 |

---

## 六、后续行动项

| 优先级 | 行动项 | 影响 |
|--------|--------|------|
| **P0** | 修复 executions 数据库迁移（`test_run_cases.test_run_id`） | 解锁 55 个 executions 用例 |
| **P0** | 修复 TestCase 删除 500 | 解锁 3 个 delete 用例 |
| **P0** | 修复 Review 创建 500 | 解锁 6 个 review create 用例 |
| **P0** | 修复 DELETE user 500（第 1 批遗留） | 解锁 1 个 user delete 用例 |
| **P1** | 放宽测试环境限流阈值 | 全量运行不被阻塞 |
| **P1** | ProjectCreateSerializer 响应加入 `id` | 减少 list 反查开销 |
| **P2** | 完成第 3-5 批测试用例 | 覆盖剩余 578 接口 |
| **P2** | 引入 jsonschema / pydantic 断言 | 提升断言 robustness |
| **P3** | 补充数据清理 finalizer | 避免测试库污染 |

---

## 七、重跑建议

待后端 BUG-1~BUG-3 修复且限流冷却后:

```bash
cd tests/api

# 1. 冒烟测试
pytest -m smoke -v

# 2. P0 核心用例
pytest -m p0 -v --tb=short

# 3. 第 2 批全量
pytest -m "testcases or executions or reviews" -v --tb=short

# 4. 生成 HTML 报告
pytest --html=report.html --self-contained-html
```
