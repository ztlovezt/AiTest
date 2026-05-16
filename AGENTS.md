# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

TestHub is an AI-driven test management platform built with Django 6.0 (backend) + Vue 3 (frontend). It provides test case management, API testing, UI automation testing, AI-powered requirement analysis, test case generation, and AI-Native precision testing capabilities (Phase 1 of TestNova roadmap).

### TestNova 演进路线（执行中）

平台正按《TestHub × TestNova 最终执行计划评审报告》(`notes/TestHub-TestNova最终执行计划评审报告.md`) 进行渐进式改造，目标 6 个月覆盖度从 59% → 81%。

**当前阶段**：Phase 1（精准测试落地）—— Week 3 / 8（Neo4j 图谱构建 + Cypher 查询）

| 周次 | 主题 | 状态 |
|------|------|------|
| Week 1 | 基础架构（13 个 Python 模块 + 6 张 MySQL 表 + Neo4j 容器化） | ✅ 已完成 |
| Week 2 | Git Diff + AST 解析引擎（GitAnalyzer/ASTAnalyzer/CoverageService/DRFRouteParser，90 单测，85% 覆盖率） | ✅ 已完成（69b734e） |
| Week 3 | Neo4j 图谱构建 + Cypher 查询（graph_builder 493行 / impact_query 343行 / verify_graph 203行 / 44新增测试 / 151累计通过） | ✅ 已完成 |
| Week 4-8 | 风险预测 / 前端 / CI Hook / DORA / 试点上线 | ⏳ 待启动 |

详细策略：`notes/精准测试设计策略方案及执行计划.md`

## Common Commands
# Activate the virtual environment(Windows)
d:\testhub_platform\venv\Scripts\Activate.ps1
# Activate the virtual environment(MacOS)
source .venv/bin/activate

### Backend (Django)

```bash
# Start development server
python start_backend.py

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run all scheduled tasks (API testing + UI automation)
python manage.py run_all_scheduled_tasks

# Initialize UI automation locator strategies
python manage.py init_locator_strategies

# Download webdrivers for UI automation
python manage.py download_webdrivers
```

### Frontend (Vue 3 + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

## Architecture

### Backend Structure (`apps/`)

The Django project uses a modular app structure under `apps/`:

- **users**: User authentication and profile management (custom User model)
- **projects**: Project and team management
- **testcases**: Manual test case management with steps, attachments, comments
- **testsuites**: Test suite organization
- **executions**: Test plan execution and result tracking
- **reports**: Test report generation
- **reviews**: Test case review workflow with templates and assignments
- **versions**: Version/release management
- **requirement_analysis**: AI-powered requirement document parsing (PDF/Word/TXT) and test case generation
- **assistant**: Dify AI chatbot integration
- **api_testing**: API testing module (HTTP/WebSocket, environments, scheduled tasks, Allure reports)
- **ui_automation**: UI automation with Selenium/Playwright, element management, page objects, AI intelligent mode
- **app_automation**: Android APP automation (Airtest 框架, 设备资源池, 组件化编排, UI Flow, 40+ REST API)
- **ai_testing**: AI 智能测试（Browser-use 文本/视觉双模式, AICase, AIIntelligentModeConfig）
- **knowledge_base**: 项目级 RAG 知识库（ChromaDB + Tika）
- **ocr_service**: 统一 OCR 服务（Tesseract + 在线大模型 + Tika 降级）
- **data_factory**: 数据工厂（51 个工具：字符/编码/随机/加密/JSON/Crontab/测试数据）
- **core**: 跨模块通用能力（统一通知配置、qcluster/init_locator_strategies/download_webdrivers 管理命令）
- **scheduler**: 调度任务管理
- **ops_tools**: 运维工具（环境管理、日志查询）
- **precision_testing**: 精准测试模块（Phase 1，Week 1-2 已完成）
  - 13 个 Python 模块（git_analyzer / ast_analyzer / coverage_service / route_parser / graph_builder / neo4j_client / risk_predictor / regression_selector / tasks / views / serializers / models / admin）
  - 6 张 MySQL 主表（precision_repo_bindings / precision_change_analyses / precision_testcase_mappings / precision_impact_analyses / precision_risk_predictions / precision_run_records）
  - Neo4j 5.28 图谱（Function/TestCase/APIEndpoint 节点 + TESTED_BY/HANDLES/CALLS/CONTAINS 关系，schema 见 `cypher/schema.cypher`）
  - 13 个 REST 端点（`/api/precision-testing/*`），含 Git Webhook、CI 覆盖率门禁、Cytoscape 图谱数据
  - 单元测试位于 `tests/precision_testing/`（90 测试，综合覆盖率 85%）

### Frontend Structure (`frontend/src/`)

- **views/**: Page components organized by feature module
- **api/**: API service layer
- **stores/**: Pinia state management
- **router/**: Vue Router configuration
- **components/**: Shared components
- **layout/**: Layout components

### Key Configuration Files

- `backend/settings.py`: Django settings (database, REST framework, CORS, Celery, email)
- `frontend/vite.config.js`: Vite build configuration
- `.env`: Environment variables (DB credentials, API keys, email config)

## API Structure

All API endpoints are prefixed with `/api/`:
- `/api/auth/` and `/api/users/`: User authentication
- `/api/projects/`: Project management
- `/api/testcases/`: Test case CRUD
- `/api/testsuites/`: Test suite management
- `/api/executions/`: Test execution
- `/api/reports/`: Report generation
- `/api/reviews/`: Review workflow
- `/api/versions/`: Version management
- `/api/assistant/`: AI assistant chat
- `/api/requirement-analysis/`: AI requirement analysis
- `/api/` (api_testing): API testing endpoints
- `/api/ui-automation/`: UI automation endpoints
- `/api/precision-testing/`: 精准测试 API（repos/analyses/mappings/impact/predictions/runs/graph/dashboard/webhooks/gate）

API documentation available at `/api/docs/` (Swagger) and `/api/redoc/` (ReDoc).

## Database & Graph

**MySQL 8.0+** with `utf8mb4` charset (主关系数据库)：
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

**Neo4j 5.28 Community**（精准测试代码图谱，Windows 原生服务，**非 Docker**）：
- `NEO4J_URI=bolt://localhost:7687`
- `NEO4J_USER=neo4j`
- `NEO4J_PASSWORD=testhub123`
- HTTP 浏览器：`http://localhost:7474`
- Schema：`backend/apps/precision_testing/cypher/schema.cypher`
- 节点：`Function` / `TestCase` / `APIEndpoint` / `Class` / `Module`
- 关系：`TESTED_BY` / `CALLS` / `HANDLES` / `CONTAINS`

**Redis 6.0+**：Django-Q2 任务队列 + 缓存

## Precision Testing Workflow（精准测试流程）

```
Git Push → Webhook → GitAnalyzer (diff) → ASTAnalyzer (变更函数+调用边)
        → Neo4j GraphBuilder (全量/增量) → ImpactQuery (Cypher 影响传播)
        → RegressionSelector (最小回归集) → CI Gate (覆盖率门禁)
```

- **全量构建**：≤5 min（中型仓库 ~10k 函数）
- **增量同步**：≤30 s（单次 commit）
- **影响查询**：3 层传播 <500 ms
- **图谱可视化**：Cytoscape.js 兼容格式（`/api/precision-testing/graph/`）

## AI Integration

The platform supports multiple AI providers configured in `requirement_analysis.AIModelConfig`:
- DeepSeek, Qwen (通义千问), SiliconFlow (硅基流动), OpenAI-compatible APIs
- AI roles: `testcase_writer`, `testcase_reviewer`, `browser_use_text`, `browser_use_vision`

UI automation AI mode uses `browser-use` library with LangChain for intelligent browser automation (`apps/ui_automation/ai_agent.py`).

## Testing Prompt Templates

Custom prompts for AI test case generation are defined in:
- `tester.md`: Test case writer persona and output format
- `tester_pro.md`: Test case reviewer persona

## Key Dependencies

**Backend 核心**：Django 6.0.1 / Django REST Framework / drf-spectacular / django-filter / Django-Q2 / channels 4.3.2 / mysqlclient 2.2.7 / httpx / selenium / playwright / browser-use 0.11.7 / langchain-openai 1.1.7 / pytesseract 0.3.10+

**精准测试模块**：
- `neo4j==5.28.0`（图谱驱动）
- `coverage==7.6.4`（动态上下文 `--cov-context=test`）
- `astroid==3.3.5`（跨模块调用边解析）
- `GitPython==3.1.43`（Git diff 解析）
- `unidiff==0.7.5`（unified diff 解析）
- `xgboost==2.1.4` + `scikit-learn==1.5.2`（风险预测，≥1000 训练样本时启用）

**Frontend**：Vue 3, Element Plus, Pinia, Vue Router, Axios, ECharts, Monaco Editor, xlsx, **Cytoscape.js**（精准测试图谱可视化）

## Commit 规范
- 默认不自动提交代码
- 多个相关修改应合并为一个 commit
- commit message 格式：`<type>: <简短描述>`
- 提交前必须运行 lint 和测试