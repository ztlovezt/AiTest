# Week 3 测试用例规格 — Neo4j 图谱构建 + Cypher 影响查询

> 对应模块: `graph_builder.py` / `impact_query.py`
> 生成日期: 2026-05-09
> 评审结论: 通过（评分 94/100）
> 覆盖目标: >= 80%

---

## 一、graph_builder.py — 图谱构建器

### 1.1 全量构建测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| GB_001 | 验证 GraphBuilder 合法路径初始化 | 本地存在合法 Git 仓库 | 1. 传入仓库根目录路径初始化 | 实例化成功，`client` 已绑定 | P0 | 单元测试 | 图谱构建 |
| GB_002 | 验证 GraphBuilder 非法路径初始化 | 路径不存在 | 1. 传入不存在的路径初始化 | 抛出 `FileNotFoundError` 或 `PathNotFoundError` | P0 | 单元测试 | 图谱构建 |
| GB_003 | 验证 GraphBuilder 默认 batch_size=500 | 传入仓库路径 | 1. 初始化后检查属性 | `self.batch_size == 500` | P1 | 单元测试 | 图谱构建 |
| GB_004 | 验证 GraphBuilder 自定义 batch_size 生效 | 传入仓库路径 | 1. 初始化时指定 `batch_size=100` | `self.batch_size == 100` | P1 | 单元测试 | 图谱构建 |
| GB_005 | 验证 apply_schema 读取 schema.cypher | schema 文件存在 | 1. 调用 `apply_schema()` | 无异常抛出，`execute_write` 被调用至少 1 次 | P0 | 单元测试 | 图谱构建 |
| GB_006 | 验证 apply_schema schema 文件不存在时警告 | schema 文件缺失 | 1. 删除 schema.cypher 后调用 | log 输出 warning，不抛异常 | P1 | 单元测试 | 图谱构建 |
| GB_007 | 验证 build_full_graph 全量构建流程 | 仓库包含多个 .py 文件 | 1. 调用 `build_full_graph()` | 返回 dict 包含 `elapsed_seconds/node_counts/function_count` | P0 | 集成测试 | 图谱构建 |
| GB_008 | 验证 build_full_graph 调用 clear_graph 清空旧数据 | 仓库已存在图数据 | 1. 调用 `build_full_graph()` | `client.clear_graph()` 被调用 1 次 | P1 | 单元测试 | 图谱构建 |
| GB_009 | 验证 build_full_graph 调用 apply_schema 应用约束 | - | 1. 调用 `build_full_graph()` | `apply_schema()` 被调用 1 次 | P1 | 单元测试 | 图谱构建 |
| GB_010 | 验证 build_full_graph 正确回调 progress | progress_callback 传入 | 1. 调用 `build_full_graph()` | 回调按顺序被调用多次（clear/scan_python/upsert_modules 等），percent 从 0 到 1.0 | P0 | 单元测试 | 图谱构建 |
| GB_011 | 验证 build_full_graph _scan_python_files 提取函数节点 | Python 源文件存在 | 1. 调用 `build_full_graph()` | `function_nodes` 列表不为空，每个节点含 `id/signature/name/start_line/end_line` | P0 | 单元测试 | 图谱构建 |
| GB_012 | 验证 build_full_graph _batch_upsert Module 节点 | Python 源文件存在 | 1. 调用 `build_full_graph()` | `client.batch_upsert_nodes` 被调用，label="Module" | P1 | 单元测试 | 图谱构建 |
| GB_013 | 验证 build_full_graph _batch_upsert Function 节点 | Python 源文件存在 | 1. 调用 `build_full_graph()` | `client.batch_upsert_nodes` 被调用，label="Function" | P1 | 单元测试 | 图谱构建 |
| GB_014 | 验证 build_full_graph 构建 CONTAINS 关系 | 函数属于某个类 | 1. 调用 `build_full_graph()` | `client.batch_create_relationships` 被调用构建 Module→Class→Function 包含关系 | P0 | 单元测试 | 图谱构建 |
| GB_015 | 验证 build_full_graph 构建 CALLS 关系 | 函数间存在调用 | 1. 调用 `build_full_graph()` | CALLS 边被创建，caller 指向 callee | P0 | 单元测试 | 图谱构建 |
| GB_016 | 验证 build_full_graph 跳过无函数的 .py 文件 | 空 .py 文件 | 1. 调用 `build_full_graph()` | 空文件不产生 Function 节点 | P1 | 单元测试 | 图谱构建 |
| GB_017 | 验证 build_full_graph 正确处理 __init__.py | 仓库含 `__init__.py` | 1. 调用 `build_full_graph()` | 模块 ID 中不含 `/__init__` 后缀，已正确规范化 | P1 | 单元测试 | 图谱构建 |
| GB_018 | 验证 build_full_graph 对嵌套类生成正确 Class 节点 ID | 源码含 `class Outer: class Inner:` | 1. 调用 `build_full_graph()` | Class 节点 ID 包含完整嵌套路径如 `apps.foo:Outer.Inner` | P1 | 单元测试 | 图谱构建 |
| GB_019 | 验证 build_full_graph 跳过非 .py 文件 | 仓库含 .txt/.md 文件 | 1. 调用 `build_full_graph()` | 非 .py 文件不被扫描，不影响性能 | P1 | 单元测试 | 图谱构建 |
| GB_020 | 验证 build_full_graph 处理 AST 解析异常不崩溃 | Python 源文件含语法错误 | 1. 调用 `build_full_graph()` | `extract_call_edges` 失败时继续执行，不抛异常 | P1 | 单元测试 | 图谱构建 |
| GB_021 | 验证 build_full_graph 正确统计返回 stats | 仓库有多个 .py 文件 | 1. 调用 `build_full_graph()` | stats 包含 `function_count/class_count/module_count/call_edge_count/api_endpoint_count` | P1 | 单元测试 | 图谱构建 |
| GB_022 | 验证 build_full_graph 时间戳 elapsed_seconds 有效 | - | 1. 调用 `build_full_graph()` | `elapsed_seconds > 0`，为合理数值 | P1 | 单元测试 | 图谱构建 |
| GB_023 | 验证 build_full_graph 读取文件使用 UTF-8 编码 | 源文件含中文注释 | 1. 调用 `build_full_graph()` | 文件正确读取不抛 `UnicodeDecodeError` | P1 | 单元测试 | 图谱构建 |
| GB_024 | 验证 build_full_graph 处理相对路径规范化 | Windows 路径包含 `\` | 1. 调用 `build_full_graph()` | 路径统一为正斜杠格式 | P1 | 单元测试 | 图谱构建 |

### 1.2 增量同步测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| GB_025 | 验证 incremental_sync 空输入直接返回 | `changed_files=[]` | 1. 调用 `incremental_sync([])` | 返回 `{"elapsed_seconds": 0.0, "files": 0, "skipped": True}` | P0 | 单元测试 | 增量同步 |
| GB_026 | 验证 incremental_sync 仅处理 .py 文件 | 变更文件含 py/txt | 1. 调用 `incremental_sync(["a.py", "b.txt"])` | 只处理 `a.py`，忽略 `b.txt` | P0 | 单元测试 | 增量同步 |
| GB_027 | 验证 incremental_sync 删除旧 Function 节点 | 文件已存在旧节点 | 1. 调用 `incremental_sync([file.py])` | `client.execute_write` 执行 `DETACH DELETE f` 语句 | P0 | 单元测试 | 增量同步 |
| GB_028 | 验证 incremental_sync 重新解析变更文件 | 变更文件含新函数 | 1. 调用 `incremental_sync([file.py])` | 新的 Function 节点被 upsert，不保留旧数据 | P0 | 单元测试 | 增量同步 |
| GB_029 | 验证 incremental_sync 更新 CALLS 边 | 变更文件含新调用关系 | 1. 调用 `incremental_sync([file.py])` | 新的 CALLS 关系被创建 | P0 | 单元测试 | 增量同步 |
| GB_030 | 验证 incremental_sync 返回正确统计 | 文件有多个函数 | 1. 调用 `incremental_sync([file.py])` | stats 包含 `function_count/call_edge_count` | P1 | 单元测试 | 增量同步 |
| GB_031 | 验证 incremental_sync 正确调用 progress 回调 | - | 1. 调用 `incremental_sync([file.py])` | 回调被调用多次（delete_old/scan_changed/done） | P1 | 单元测试 | 增量同步 |
| GB_032 | 验证 incremental_sync 跳过不含 .py 的变更 | 变更文件无 .py | 1. 调用 `incremental_sync(["README.md"])` | 返回 `skipped: True`，不执行任何 Cypher | P0 | 单元测试 | 增量同步 |

### 1.3 批量写入测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| GB_033 | 验证 _batch_upsert 分片正确 | 节点数 > batch_size | 1. 构造 1000 个节点，batch_size=500 调用 | `batch_upsert_nodes` 被调用 2 次，每次 500 条 | P0 | 单元测试 | 批量写入 |
| GB_034 | 验证 _batch_upsert 节点数为 0 时不调用 | nodes=[] | 1. 调用 `_batch_upsert("Module", [])` | `client.batch_upsert_nodes` 不被调用 | P1 | 单元测试 | 批量写入 |
| GB_035 | 验证 _batch_create_rels 分片正确 | 关系数 > batch_size | 1. 构造 1000 个关系，batch_size=500 调用 | `client.batch_create_relationships` 被调用 2 次 | P0 | 单元测试 | 批量写入 |
| GB_036 | 验证 _batch_create_rels 关系数为 0 时不调用 | rels=[] | 1. 调用 `_batch_create_rels(..., [])` | `client.batch_create_relationships` 不被调用 | P1 | 单元测试 | 批量写入 |

### 1.4 内部方法测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| GB_037 | 验证 _scan_python_files only 参数筛选文件 | only=[file1.py, file2.py] | 1. 调用 `_scan_python_files(only=["a.py"])` | 只扫描指定文件，不扫描全仓库 | P0 | 单元测试 | 文件扫描 |
| GB_038 | 验证 _scan_python_files 处理文件不存在 | only 包含不存在的文件 | 1. 调用 `_scan_python_files(only=["nonexistent.py"])` | 不抛异常，跳过不存在文件 | P1 | 单元测试 | 文件扫描 |
| GB_039 | 验证 _resolve_callee 精确匹配签名 | callee_module + callee_name 可拼接 | 1. 调用 `_resolve_callee(edge, signatures, name_index)` | 返回精确匹配的 signature | P0 | 单元测试 | 调用解析 |
| GB_040 | 验证 _resolve_callee 按短名称唯一匹配 | callee_name 在索引中唯一 | 1. 调用 `_resolve_callee(edge, signatures, name_index)` | 短名称唯一时返回匹配结果 | P0 | 单元测试 | 调用解析 |
| GB_041 | 验证 _resolve_callee 多匹配时返回 None | callee_name 对应多个候选 | 1. 调用 `_resolve_callee(edge, signatures, name_index)` | 返回 `None`（避免歧义） | P1 | 单元测试 | 调用解析 |
| GB_042 | 验证 _resolve_callee 自身调用不连边 | caller == target_sig | 1. 调用 `_resolve_callee`，返回与 caller 相同 | 调用方跳过自身调用 | P1 | 单元测试 | 调用解析 |
| GB_043 | 验证 _module_dotted_from_path 普通模块 | `apps/foo/bar.py` | 1. 调用函数 | 返回 `apps.foo.bar` | P0 | 单元测试 | 路径转换 |
| GB_044 | 验证 _module_dotted_from_path __init__ 模块 | `apps/foo/__init__.py` | 1. 调用函数 | 返回 `apps.foo`（去除 `/__init__`） | P0 | 单元测试 | 路径转换 |
| GB_045 | 验证 _module_dotted_from_path Windows 路径 | `apps\foo\bar.py` | 1. 调用函数 | 返回 `apps.foo.bar`（统一正斜杠） | P0 | 单元测试 | 路径转换 |
| GB_046 | 验证 _iter_cypher_statements 正确拆分语句 | 含注释和空行的 cypher | 1. 调用函数 | 返回不含注释行和空语句的列表 | P0 | 单元测试 | Schema 解析 |
| GB_047 | 验证 _iter_cypher_statements 忽略单行注释 | `// comment` 行 | 1. 调用函数 | 注释行不被返回 | P0 | 单元测试 | Schema 解析 |
| GB_048 | 验证 _scan_testcases 从 Django ORM 读取用例 | TestCase 表有数据 | 1. 调用 `_scan_testcases()` | 返回列表每项含 `id/title/test_type/priority` | P0 | 单元测试 | 用例扫描 |
| GB_049 | 验证 _scan_testcases 表为空时返回空列表 | TestCase 表无数据 | 1. 调用 `_scan_testcases()` | 返回 `[]` | P0 | 单元测试 | 用例扫描 |
| GB_050 | 验证 _build_tested_by_relationships 批量建立关系 | Mapping 表有记录 | 1. 调用 `_build_tested_by_relationships()` | `batch_create_relationships` 被调用，`type="manual/automatic"` | P0 | 单元测试 | 关系构建 |
| GB_051 | 验证 _build_contains 按标签分桶正确 | CONTAINS 关系含多种类型 | 1. 调用 `_build_contains(edges)` | 按 (from_label, to_label) 分组后分别写入 | P0 | 单元测试 | 关系构建 |
| GB_052 | 验证 _build_contains edges 为空时不调用 | edges=[] | 1. 调用 `_build_contains([])` | `batch_create_relationships` 不被调用 | P1 | 单元测试 | 关系构建 |
| GB_053 | 验证 _scan_api_endpoints 调用 DRFRouteParser | ROOT_URLCONF 已配置 | 1. 调用 `_scan_api_endpoints()` | `DRFRouteParser.parse()` 被调用 | P0 | 单元测试 | API 端点 |
| GB_054 | 验证 _scan_api_endpoints 生成端点 ID 唯一 | 多个端点 | 1. 调用 `_scan_api_endpoints()` | 端点 ID 格式 `{http_method} /{url_pattern}`，不重复 | P0 | 单元测试 | API 端点 |
| GB_055 | 验证 _scan_api_endpoints 生成 HANDLES 关系 | 端点绑定到函数 | 1. 调用 `_scan_api_endpoints()` | handles 列表含 from_id(端点) 和 to_id(函数签名) | P0 | 单元测试 | API 端点 |
| GB_056 | 验证 _scan_api_endpoints ROOT_URLCONF 未配置时返回空 | 未配置 | 1. 调用 `_scan_api_endpoints()` | 返回 `([], [])`，不抛异常 | P1 | 单元测试 | API 端点 |
| GB_057 | 验证 _scan_api_endpoints 解析失败时降级 | URLConf 文件不存在 | 1. 调用 `_scan_api_endpoints()` | 返回 `([], [])`，log 输出 warning | P1 | 单元测试 | API 端点 |

---

## 二、impact_query.py — 影响查询

### 2.1 核心影响传播测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| IQ_001 | 验证 ImpactQuery 合法初始化 | Neo4j 服务正常 | 1. 初始化 `ImpactQuery()` | 实例化成功，`client` 已绑定 | P0 | 单元测试 | 影响查询 |
| IQ_002 | 验证 query_impact 空输入直接返回 | `changed_function_ids=[]` | 1. 调用 `query_impact([])` | 返回 `ImpactResult(changed=[], impacted=[], testcases=[], endpoints=[])` | P0 | 单元测试 | 影响查询 |
| IQ_003 | 验证 query_impact 深度限制生效 | depth=100（超出 MAX_DEPTH=8） | 1. 调用 `query_impact(ids, depth=100)`<br>2. 检查返回 result.depth | depth 被限制为 `MAX_DEPTH=8`，result.depth == 8 | P0 | 单元测试 | 影响查询 |
| IQ_004 | 验证 query_impact 深度最小值保护 | depth=0 或负数 | 1. 调用 `query_impact(ids, depth=0)`<br>2. 检查返回 result.depth | depth 被调整为最小值 1 | P0 | 单元测试 | 影响查询 |
| IQ_005 | 验证 query_impact 返回完整 ImpactResult | 存在变更函数 | 1. 调用 `query_impact(["sig1", "sig2"])` | 返回包含 `changed_functions/impacted_functions/impacted_testcases/impacted_endpoints/depth/elapsed_ms` | P0 | 单元测试 | 影响查询 |
| IQ_006 | 验证 query_impact 包含路径时触发 _query_propagation_paths | `include_paths=True` | 1. 调用 `query_impact(ids, include_paths=True)` | `propagation_paths` 列表不为空 | P0 | 单元测试 | 影响查询 |
| IQ_007 | 验证 query_impact 变更函数自身并入受影响集 | 单个变更函数无传播 | 1. 调用 `query_impact([sig1], depth=1)` | `impacted_functions` 包含 `sig1` | P0 | 单元测试 | 影响查询 |
| IQ_008 | 验证 query_impact 正确查询 TESTED_BY 关系 | Function 有对应 TestCase | 1. 调用 `query_impact([sig])` | `impacted_testcases` 包含关联的 testcase_id | P0 | 单元测试 | 影响查询 |
| IQ_009 | 验证 query_impact 正确查询 HANDLES 关系 | APIEndpoint 关联 Function | 1. 调用 `query_impact([sig])` | `impacted_endpoints` 包含关联的 endpoint_id | P0 | 单元测试 | 影响查询 |
| IQ_010 | 验证 query_impact 性能目标达成 | 3 层传播 | 1. 调用 `query_impact(ids, depth=3)` 并计时 | `elapsed_ms < 500`（中型仓库 ~10k 函数 / ~30k 调用边） | P0 | 性能测试 | 影响查询 |

### 2.2 子图查询测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| IQ_011 | 验证 query_subgraph 以节点为中心拉取邻域 | Neo4j 图谱有数据 | 1. 调用 `query_subgraph(node_id="sig", depth=2)` | 返回 `{"nodes": [...], "edges": [...]}` | P0 | 单元测试 | 子图查询 |
| IQ_012 | 验证 query_subgraph node_limit 限制节点数 | 图谱节点数 > limit | 1. 调用 `query_subgraph(node_id, node_limit=50)` | 返回节点数 ≤ 50（加上 center 本身） | P1 | 单元测试 | 子图查询 |
| IQ_013 | 验证 query_subgraph 深度限制生效 | depth > MAX_DEPTH | 1. 调用 `query_subgraph(node_id, depth=100)` | depth 被限制为 MAX_DEPTH=8 | P1 | 单元测试 | 子图查询 |
| IQ_014 | 验证 query_subgraph 节点不存在时返回空图 | 无效 node_id | 1. 调用 `query_subgraph(node_id="nonexistent")` | 返回 `{"nodes": [], "edges": []}` | P1 | 单元测试 | 子图查询 |

### 2.3 全图查询测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| IQ_015 | 验证 query_overview 全图采样 | 图谱有数据 | 1. 调用 `query_overview()` | 返回 Cytoscape 格式，`nodes` 和 `edges` 非空 | P0 | 单元测试 | 全图查询 |
| IQ_016 | 验证 query_overview 按 node_type 过滤 | node_type="Function" | 1. 调用 `query_overview(node_type="Function")` | 仅返回 Function 节点，`labels` 为 `["Function"]` | P0 | 单元测试 | 全图查询 |
| IQ_017 | 验证 query_overview limit 参数限制数量 | limit=10 | 1. 调用 `query_overview(limit=10)` | 返回节点数 ≤ 10 | P1 | 单元测试 | 全图查询 |
| IQ_018 | 验证 query_overview 无效 node_type 抛异常 | node_type="InvalidType" | 1. 调用 `query_overview(node_type="InvalidType")` | 抛出 `ValueError`，消息提示允许的节点类型 | P0 | 单元测试 | 全图查询 |

### 2.4 内部 Cypher 查询测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| IQ_019 | 验证 _safe_label 白名单校验通过 | label="Function" | 1. 调用 `_safe_label("Function")` | 返回 `"Function"` | P0 | 单元测试 | 标签校验 |
| IQ_020 | 验证 _safe_label 非法标签抛 ValueError | label="HackerNode" | 1. 调用 `_safe_label("HackerNode")` | 抛出 `ValueError` | P0 | 单元测试 | 标签校验 |
| IQ_021 | 验证 ImpactResult.to_dict 可 JSON 序列化 | - | 1. 调用 `result.to_dict()` 后 `json.dumps()` | 不抛异常，结构符合 API 约定 | P0 | 单元测试 | 结果序列化 |
| IQ_022 | 验证 _node_dict 正确排除 id 字段覆盖 | props 含 id | 1. 调用 `_node_dict(internal_id, labels, {"id": "business_id", "name": "func"})` | `data.id` 使用内部 id 而非业务 id | P0 | 单元测试 | Cytoscape 序列化 |
| IQ_023 | 验证 _node_dict name 回退到 id | props 无 name/title/qualified_name | 1. 调用 `_node_dict(internal_id, labels, {"id": "sig"})` | `data.name` 为 `"sig"` | P1 | 单元测试 | Cytoscape 序列化 |
| IQ_024 | 验证 _edge_dict 正确生成唯一边 ID | source/target/rel_type | 1. 调用 `_edge_dict(1, 2, "CALLS", None)` | 返回 `{"data": {"id": "e1-2-CALLS", ...}}` | P0 | 单元测试 | Cytoscape 序列化 |
| IQ_025 | 验证 _records_to_cytoscape 去重节点 | 同一节点在多个路径中出现 | 1. 调用 `_records_to_cytoscape(records)` | 返回 nodes 列表无重复 | P0 | 单元测试 | Cytoscape 序列化 |
| IQ_026 | 验证 _records_to_cytoscape 去重边 | 同一边在多个路径中出现 | 1. 调用 `_records_to_cytoscape(records)` | 返回 edges 列表无重复 | P0 | 单元测试 | Cytoscape 序列化 |
| IQ_027 | 验证 get_impact_query 工厂函数返回实例 | - | 1. 调用 `get_impact_query()` | 返回 `ImpactQuery` 实例 | P0 | 单元测试 | 工厂函数 |
| IQ_028 | 验证 query_impact 日志记录关键指标 | - | 1. 调用 `query_impact(ids, depth=3)` | logger.info 记录 changed/impacted/testcases/endpoints/elapsed_ms | P1 | 单元测试 | 日志记录 |
| IQ_029 | 验证 _query_impacted_functions 不返回变更函数自身 | 仅有自身 | 1. 调用 `_query_impacted_functions([sig], depth=1)` | 返回空列表（自身不算"上游"） | P0 | 单元测试 | 上游查询 |
| IQ_030 | 验证 _query_testcases_for_functions 空输入返回空 | `function_ids=[]` | 1. 调用 `_query_testcases_for_functions([])` | 返回 `[]` | P0 | 单元测试 | 用例查询 |
| IQ_031 | 验证 _query_endpoints_for_functions 空输入返回空 | `function_ids=[]` | 1. 调用 `_query_endpoints_for_functions([])` | 返回 `[]` | P0 | 单元测试 | 端点查询 |
| IQ_032 | 验证 _query_propagation_paths 返回跳数排序 | 多个路径 | 1. 调用 `_query_propagation_paths(ids, depth=3)` | 返回列表按 `hops` 升序排列，最多 100 条 | P0 | 单元测试 | 路径查询 |
| IQ_033 | 验证 _records_to_cytoscape 处理 None neighbor | paths 含 None 节点 | 1. 调用 `_records_to_cytoscape(records_with_none)` | None 被跳过，不影响其他节点 | P1 | 单元测试 | 序列化容错 |
| IQ_034 | 验证 _records_to_cytoscape 处理 None relationship | paths 含 None rel | 1. 调用 `_records_to_cytoscape(records_with_none_rel)` | None 被跳过，不影响其他边 | P1 | 单元测试 | 序列化容错 |
| IQ_035 | 验证 query_subgraph Cytoscape 节点格式正确 | 节点有完整属性 | 1. 调用 `query_subgraph(node_id, depth=1)` | nodes 每项含 `data{id/label/name/node_type/node_id}` 和 `classes` | P0 | 单元测试 | 格式验证 |
| IQ_036 | 验证 query_subgraph Cytoscape 边格式正确 | 边有完整属性 | 1. 调用 `query_subgraph(node_id, depth=1)` | edges 每项含 `data{id/source/target/label/rel_type}` 和 `classes` | P0 | 单元测试 | 格式验证 |

---

## 三、API 视图测试

### 3.1 GraphDataView 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| VC_001 | 验证 GraphDataView GET 请求返回 200 | Neo4j 图谱有数据 | 1. GET `/api/precision-testing/graph/` | 返回 200，body 含 `nodes/edges` | P0 | API测试 | 图谱可视化 |
| VC_002 | 验证 GraphDataView 支持 node_type 参数过滤 | node_type="Function" | 1. GET `/api/precision-testing/graph/?node_type=Function` | 返回仅含 Function 节点的图 | P0 | API测试 | 图谱可视化 |
| VC_003 | 验证 GraphDataView 支持 center 参数定位节点 | 节点存在 | 1. GET `/api/precision-testing/graph/?center=apps.module:func` | 返回以指定节点为中心的子图 | P1 | API测试 | 图谱可视化 |
| VC_004 | 验证 GraphDataView 支持 label 参数显示标签 | label="func_name" | 1. GET `/api/precision-testing/graph/?label=func_name` | 返回节点标签可见 | P1 | API测试 | 图谱可视化 |
| VC_005 | 验证 GraphDataView 支持 depth 参数控制深度 | depth=2 | 1. GET `/api/precision-testing/graph/?depth=2` | 返回 2 层邻域子图 | P1 | API测试 | 图谱可视化 |
| VC_006 | 验证 GraphDataView 支持 limit 参数限制数量 | limit=50 | 1. GET `/api/precision-testing/graph/?limit=50` | 返回节点数 ≤ 50 | P1 | API测试 | 图谱可视化 |
| VC_007 | 验证 GraphDataView 无效 node_type 返回 400 | node_type="Invalid" | 1. GET `/api/precision-testing/graph/?node_type=Invalid` | 返回 400，错误信息提示允许的节点类型 | P0 | API测试 | 输入校验 |
| VC_008 | 验证 GraphDataView center 不存在时返回空图 | 无效 center | 1. GET `/api/precision-testing/graph/?center=nonexistent` | 返回 `{"nodes": [], "edges": []}` | P1 | API测试 | 容错处理 |

### 3.2 ImpactQueryView 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| IQAPI_001 | 验证 ImpactQueryView POST 请求返回 200 | 请求格式正确 | 1. POST `/api/precision-testing/impact/query/` body=`{"changed_functions": ["sig"]}` | 返回 200，`result` 包含 ImpactResult | P0 | API测试 | 影响查询API |
| IQAPI_002 | 验证 ImpactQueryView 空 changed_functions 返回空结果 | 空列表 | 1. POST `/api/precision-testing/impact/query/` body=`{"changed_functions": []}` | 返回 200，`impacted_functions` 等为空 | P0 | API测试 | 影响查询API |
| IQAPI_003 | 验证 ImpactQueryView 支持 include_paths 参数 | `include_paths=True` | 1. POST body=`{"changed_functions": ["sig"], "include_paths": true}` | 返回结果包含 `propagation_paths` | P0 | API测试 | 影响查询API |
| IQAPI_004 | 验证 ImpactQueryView depth 参数限制传播层数 | depth=2 | 1. POST body=`{"changed_functions": ["sig"], "depth": 2}` | 影响传播深度限制为 2 层 | P0 | API测试 | 影响查询API |
| IQAPI_005 | 验证 ImpactQueryView 无效 node_type 返回 400 | node_type 参数无效 | 1. POST body=`{"node_type": "InvalidType"}` | 返回 400，错误信息明确 | P0 | API测试 | 输入校验 |
| IQAPI_006 | 验证 ImpactQueryView 缺少 changed_functions 字段返回 400 | 字段缺失 | 1. POST body=`{}` | 返回 400，提示 `changed_functions` 必填 | P0 | API测试 | 输入校验 |
| IQAPI_007 | 验证 ImpactQueryView 非法 JSON 返回 400 | 非 JSON body | 1. POST 纯文本 `"not json"` | 返回 400 | P0 | API测试 | 输入校验 |

---

## 四、配置与 CLI 测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| SYNC_001 | 验证 verify_graph 命令存在 | Django 管理命令 | 1. `python manage.py verify_graph --help` | 输出帮助信息，包含 `--json` 和 `--fix-orphans` 选项 | P0 | 配置测试 | 图谱校验 |
| SYNC_002 | 验证 verify_graph --json 输出 JSON 格式 | 图谱有数据 | 1. `python manage.py verify_graph --json` | stdout 输出有效 JSON | P0 | 配置测试 | 图谱校验 |
| SYNC_003 | 验证 verify_graph --fix-orphans 修复孤立节点 | 图谱含孤立节点 | 1. `python manage.py verify_graph --fix-orphans` | 孤立节点被清理或修复 | P1 | 配置测试 | 图谱校验 |

---

## 五、性能测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| SYNC_004 | 验证增量同步 5 个文件性能达标 | 5 个 .py 文件变更，中型仓库（~10k 函数节点） | 1. 调用 `incremental_sync([5 files])` 计时 | `elapsed_seconds < 30` | P0 | 性能测试 | 增量同步 |
| SYNC_005 | 验证增量同步时间预算内完成 | 时间预算 900s | 1. 调用 `incremental_sync()` 处理较大变更集 | 完成时间远小于 900s | P1 | 性能测试 | 增量同步 |

---

## 六、Neo4j 客户端测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| NEO4J_001 | 验证 Neo4j 连接单例模式 | Neo4j 服务正常 | 1. 调用 `get_neo4j_client()` 两次 | 两次返回同一实例（连接池复用） | P0 | 单元测试 | Neo4j连接 |
| NEO4J_002 | 验证 Neo4j 服务不可用时抛出异常 | Neo4j 停止 | 1. 调用 `get_neo4j_client()` | 抛出连接异常，不静默失败 | P0 | 容错测试 | Neo4j连接 |
| NEO4J_003 | 验证 batch_upsert_nodes 分批正确 | 节点数 > batch_size | 1. 调用 `batch_upsert_nodes("Function", nodes, key="id")` | UNWIND 批量写入，每批 500 条 | P0 | 单元测试 | 批量写入 |
| NEO4J_004 | 验证 batch_create_relationships 关系去重 | 关系可能重复 | 1. 调用 `batch_create_relationships(...)` | 相同关系不会被创建多次 | P1 | 单元测试 | 关系创建 |
| NEO4J_005 | 验证 clear_graph 清空所有节点和边 | 图谱有数据 | 1. 调用 `clear_graph()` | 所有节点和边被删除 | P0 | 单元测试 | 图谱清空 |
| NEO4J_006 | 验证 execute_read 查询超时处理 | 查询耗时过长 | 1. 调用 `execute_read()` 执行复杂查询 | 超时时抛出异常或返回空结果 | P1 | 容错测试 | 查询超时 |
| NEO4J_007 | 验证 count_nodes 返回准确数量 | 图谱有数据 | 1. 调用 `count_nodes()` | 返回 `{Function: n, Class: m, ...}` 格式 | P0 | 单元测试 | 节点统计 |

---

## 七、E2E 集成测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| E2E_001 | 验证端到端变更分析流程 | 有 commit 变更 | 1. 触发变更分析任务<br>2. 调用 `query_impact()`<br>3. 检查最小回归集 | 最终输出包含变更影响的测试用例列表 | P0 | E2E测试 | 端到端流程 |
| E2E_002 | 验证增量同步后图谱数据一致性 | 增量更新后 | 1. 执行增量同步<br>2. 查询受影响函数 | 新函数节点存在，旧节点已清理 | P0 | E2E测试 | 数据一致性 |
| E2E_003 | 验证全量构建后图谱完整性 | 全量构建完成 | 1. 执行 `build_full_graph()`<br>2. 验证所有节点类型数量 | Function/Class/Module/TestCase/APIEndpoint 节点存在 | P0 | E2E测试 | 数据完整性 |
| E2E_004 | 验证子图查询返回前端可用格式 | 前端请求子图 | 1. 前端调用 GraphDataView<br>2. 检查返回 JSON | 格式符合 Cytoscape.js 要求，可直接渲染 | P0 | E2E测试 | 前端兼容 |

---

## 八、安全测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| AUTH_001 | 验证未授权访问被拒绝 | 用户未登录 | 1. GET `/api/precision-testing/graph/` | 返回 401 未授权错误 | P0 | 安全测试 | 权限校验 |
| AUTH_002 | 验证 ImpactQueryView 未授权访问被拒绝 | 用户未登录 | 1. POST `/api/precision-testing/impact/query/` | 返回 401 未授权错误 | P0 | 安全测试 | 权限校验 |

---

## 九、数据库测试

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|--------|--------|--------|--------|--------|--------|--------|
| DB_001 | 验证 TestCaseCodeMapping 模型约束 | 数据库迁移完成 | 1. 检查表结构 | 包含 `function_signature/testcase_id/confidence/mapping_type` 字段 | P0 | 数据库测试 | 数据模型 |
| DB_002 | 验证 precision_* 表索引存在 | 数据库有数据 | 1. 检查索引 | `function_signature` 和 `testcase_id` 有索引加速查询 | P1 | 数据库测试 | 索引验证 |

---

## 测试覆盖率汇总

| 模块 | 测试用例数 | 测试类型分布 |
|------|-----------|------------|
| `graph_builder.py` | 57 | 单元测试 49 / 集成测试 1 / 配置测试 3 / 性能测试 2 / E2E测试 2 |
| `impact_query.py` | 36 | 单元测试 30 / API测试 4 / 性能测试 1 / 安全测试 1 |
| API 视图 | 15 | API测试 15 |
| Neo4j 客户端 | 7 | 单元测试 5 / 容错测试 2 |
| 数据库/安全 | 4 | 数据库测试 2 / 安全测试 2 |
| **合计** | **119** | — |

---

## 场景类型覆盖率

三要素模型全部覆盖：

| 场景类型 | 覆盖情况 |
|----------|---------|
| 正常（Positive） | ✅ 所有模块 |
| 边界（Boundary） | ✅ depth 边界/空列表/最大分片 |
| 异常（Anomaly） | ✅ Neo4j 不可用/文件不存在/空输入 |
| 组合（Combination） | ✅ E2E 全链路测试 |
| 性能（Performance） | ✅ 增量同步<30s/影响查询<500ms |
| 安全（Security） | ✅ 权限校验/API 输入校验 |

---

## 备注

- 测试策略：**算法层单元测试**优先（mock Neo4j），**集成测试**依赖 Neo4j 联机
- Week 3 覆盖率和测试执行预计在 Neo4j 容器启动后进行
- `verify_graph` 管理命令提供图谱数据校验能力
- 所有 API 测试需认证（JWT Token）