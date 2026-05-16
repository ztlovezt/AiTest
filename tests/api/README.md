# testhub-platform 接口自动化测试

基于 [`/scripts/testhub_api_swagger2.json`](../../scripts/testhub_api_swagger2.json) 与后端真实代码生成,使用 pytest + requests 实现。

## 覆盖范围

### 第 1 批(已完成,基础模块)

| 模块 | 接口数 | 用例数 | 文件 |
|------|--------|--------|------|
| auth | 13 | 39 | `test_auth.py` |
| projects | 13 | 19 | `test_projects.py` |
| users (alias) | 13 | 6 | `test_users.py` |
| **小计** | **39** | **64** | — |

### 第 2 批(测试管理三件套)

| 模块 | 接口数 | 用例数 | 文件 |
|------|--------|--------|------|
| testcases | 9 | 30 | `test_testcases.py` |
| executions | 23 | 55 | `test_executions.py` |
| reviews | 21 | 55 | `test_reviews.py` |
| **小计** | **53** | **140** | — |

### 合计

| 总接口 | 总用例 | 文件 |
|--------|--------|------|
| **92** | **204** | 6 |

> 后续批次(第 3-5 批)规划见 [`TEST_PLAN.md`](TEST_PLAN.md);第 2 批详细用例文档见 [`testcases_phase2.md`](testcases_phase2.md)。

## 六维场景分布

| 场景类型 | 用例数 | 标记 |
|---------|--------|------|
| Positive 正向 | 18 | `@pytest.mark.positive` |
| Boundary 边界 | 5 | `@pytest.mark.boundary` |
| Anomaly 异常 | 22 | `@pytest.mark.anomaly` |
| Combination 组合 | 7 | `@pytest.mark.combination` |
| Security 安全 | 6 | `@pytest.mark.security` |
| Performance 性能 | 0 | (未启用,需独立压测工具) |

## 快速开始

### 1. 安装依赖

```bash
cd tests/api
pip install -r requirements.txt
```

### 2. 启动后端

```bash
cd backend
python manage.py runserver 127.0.0.1:8000
```

### 3. 运行测试

```bash
cd tests/api

# 全量
pytest

# 仅冒烟用例 (P0 + Positive)
pytest -m "smoke"

# 仅 auth 模块
pytest -m "auth"

# 第 2 批(测试管理三件套)
pytest -m "testcases or executions or reviews"

# 仅 testcases / executions / reviews 单模块
pytest -m "testcases"
pytest -m "executions"
pytest -m "reviews"

# 仅安全场景
pytest -m "security"

# 排除需评审的不稳定用例
pytest -m "not review_required"

# 并行执行 (4 worker)
pytest -n 4

# 生成 HTML 报告
pytest --html=report.html --self-contained-html
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TESTHUB_BASE_URL` | `http://127.0.0.1:8000` | 后端服务地址 |
| `TESTHUB_TIMEOUT` | `10` | HTTP 超时(秒) |
| `TESTHUB_TEST_USERNAME` | (空) | 已存在的测试账号 |
| `TESTHUB_TEST_PASSWORD` | (空) | 测试账号密码 |
| `TESTHUB_ADMIN_USERNAME` | (空) | 管理员账号(仅部分用例需要) |
| `TESTHUB_ADMIN_PASSWORD` | (空) | 管理员密码 |

> 当前 conftest 默认通过 `/api/auth/register/` 自动注册临时用户作为测试账号,
> 因此**不需要预置账号**即可运行大多数用例。

## 测试用例标签体系

### 优先级
- `@pytest.mark.smoke` — 冒烟用例(主流程,必跑)
- `@pytest.mark.p0` — 核心功能(每次构建必跑)
- `@pytest.mark.p1` — 重要功能(回归必跑)
- `@pytest.mark.p2` — 一般功能(完整回归)

### 场景类型
- `@pytest.mark.positive` — 正向流程
- `@pytest.mark.boundary` — 边界值
- `@pytest.mark.anomaly` — 异常场景
- `@pytest.mark.combination` — 跨接口组合
- `@pytest.mark.security` — 安全场景
- `@pytest.mark.performance` — 性能场景

### 模块
- `@pytest.mark.auth` / `@pytest.mark.projects` / `@pytest.mark.users`

### 评审标识
- `@pytest.mark.review_required` — **置信度 LOW**,需人工评审。
  涉及 swagger 未声明 schema、依赖外部数据、业务规则不明确的用例。

## 置信度说明 (AI 生成原则要求)

| 级别 | 含义 | 用例数 |
|------|------|--------|
| HIGH | 输入完整(swagger + 真实代码),约束明确 | 60 |
| MEDIUM | 部分依赖外部数据(成员/环境配置) | 2 |
| LOW (`review_required`) | swagger 未声明 schema、需人工评审 | 2 |

**LOW 用例清单**(必须人工评审):
- `test_users_create_p001_via_user_serializer` — UserSerializer 不含 password,
  实际行为依赖 User model 字段默认值
- `test_env_create_p001` — ProjectEnvironment 字段集需对照模型确认

## 已知限制

1. **不覆盖性能场景**: 单元 pytest 不适合压测,建议用 locust/k6 单独覆盖。
2. **未覆盖前端 UI**: 仅接口层,UI 交互需 Selenium/Playwright。
3. **不覆盖 api-testing 等大模块**: 已归属其它 89 个接口,可后续扩展。
4. **数据隔离**: 测试默认创建临时用户/项目,但**不会自动清理**;
   建议测试环境定期清库或在 conftest 中加 finalizer。

## 扩展指南

### 新增模块测试

1. 复制 `test_projects.py` 作为模板
2. 在 `conftest.py` 添加该模块的 fixture(如 `created_xxx`)
3. 按六维场景为每个接口写 3-7 个用例
4. 在 `pytest.ini` 注册新 marker
5. 更新本 README 的覆盖表与 `testcases.md`

### 反馈循环

执行结果中的失败用例反映:
- **断言不准** → 优化 assertion(对照实际响应)
- **接口规范变更** → 重生成 swagger 后重跑
- **真实 bug** → 在 issue 跟踪,保留用例作为回归

## 文件清单

```
tests/api/
├── conftest.py          # pytest 公共 fixture
├── pytest.ini           # pytest 配置 + marker 注册
├── requirements.txt     # 依赖
├── test_auth.py         # auth 13 接口 / 39 用例
├── test_projects.py     # projects 13 接口 / 19 用例
├── test_users.py        # users 别名一致性 / 6 用例
├── testcases.md         # Markdown 用例文档(评审用)
└── README.md            # 本文件
```
