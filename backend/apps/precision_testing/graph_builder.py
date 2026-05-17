"""图构建器 — 将 Django ORM 数据 + AST 解析结果同步到 Neo4j

Week 3 增强：
- 全量 / 增量两种构建模式
- CALLS 调用关系（跨模块，astroid 推断）
- CONTAINS 包含关系（Module→Class→Function）
- 进度回调（供 Django-Q2 任务汇报百分比）
- schema.cypher 自动应用（约束 + 索引）
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from django.conf import settings

from .neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]
"""进度回调签名：(stage_name, percent_0_to_1)"""

DEFAULT_BATCH_SIZE = 500
DEFAULT_CALL_DEPTH_LIMIT = 5  # CALLS 关系最大可达深度（用于影响查询）


def _noop(stage: str, percent: float) -> None:  # pragma: no cover - 空回调
    return None


class GraphBuilder:
    """扫描代码仓库，将函数 / 类 / 模块 / 用例 / API 节点及关系写入 Neo4j。"""

    def __init__(
        self,
        repo_path: str,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.repo_path = Path(repo_path)
        self.batch_size = batch_size
        self.client = get_neo4j_client()
        self._progress: ProgressCallback = progress_callback or _noop

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def apply_schema(self) -> None:
        """应用 schema.cypher 中的约束 + 索引（幂等）。"""
        schema_file = Path(__file__).parent / "cypher" / "schema.cypher"
        if not schema_file.exists():
            logger.warning("schema.cypher 不存在: %s", schema_file)
            return
        for stmt in self._iter_cypher_statements(schema_file.read_text(encoding="utf-8")):
            try:
                self.client.execute_write(stmt)
            except Exception as exc:  # pragma: no cover - Neo4j 版本兼容性兜底
                logger.warning("schema 语句执行失败 (%s): %s", stmt[:60], exc)

    @staticmethod
    def _iter_cypher_statements(text: str) -> Iterable[str]:
        """从 cypher 文件中拆分出可执行语句（忽略注释行、空语句）。"""
        for raw in text.split(";"):
            cleaned = "\n".join(
                ln for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("//")
            ).strip()
            if cleaned:
                yield cleaned

    # ------------------------------------------------------------------
    # 全量构建
    # ------------------------------------------------------------------
    def build_full_graph(self) -> dict[str, Any]:
        """全量重建图（会清空现有图数据）。返回构建统计。"""
        start_ts = time.monotonic()
        logger.info("Starting full graph build for %s", self.repo_path)
        self._progress("clear", 0.0)
        self.client.clear_graph()
        self.apply_schema()

        # Step 1: 扫描所有 Python 文件（一次性收集 Function / Class / Module + CALLS）
        self._progress("scan_python", 0.05)
        scan_result = self._scan_python_files()
        function_nodes = scan_result["functions"]
        class_nodes = scan_result["classes"]
        module_nodes = scan_result["modules"]
        call_edges = scan_result["call_edges"]
        contains_edges = scan_result["contains_edges"]

        # Step 2: 写入节点
        self._progress("upsert_modules", 0.30)
        self._batch_upsert("Module", module_nodes)
        self._progress("upsert_classes", 0.40)
        self._batch_upsert("Class", class_nodes)
        self._progress("upsert_functions", 0.50)
        self._batch_upsert("Function", function_nodes)

        # Step 3: TestCase 节点
        self._progress("upsert_testcases", 0.65)
        testcase_nodes = self._scan_testcases()
        self._batch_upsert("TestCase", testcase_nodes)

        # Step 4: 关系
        self._progress("contains_edges", 0.75)
        self._build_contains(contains_edges)

        self._progress("calls_edges", 0.82)
        self._build_calls(call_edges, function_signatures={n["id"] for n in function_nodes})

        self._progress("tested_by", 0.90)
        self._build_tested_by_relationships()

        # Step 5: API endpoints
        self._progress("api_endpoints", 0.95)
        api_nodes, api_handles = self._scan_api_endpoints()
        if api_nodes:
            self._batch_upsert("APIEndpoint", api_nodes)
        if api_handles:
            self._batch_create_rels("APIEndpoint", "id", "HANDLES", "Function", "id", api_handles)

        elapsed = time.monotonic() - start_ts
        stats = {
            "elapsed_seconds": round(elapsed, 2),
            "node_counts": self.client.count_nodes(),
            "function_count": len(function_nodes),
            "class_count": len(class_nodes),
            "module_count": len(module_nodes),
            "call_edge_count": len(call_edges),
            "api_endpoint_count": len(api_nodes),
        }
        self._progress("done", 1.0)
        logger.info("Full graph build completed in %.2fs: %s", elapsed, stats)
        return stats

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------
    def incremental_sync(self, changed_files: list[str]) -> dict[str, Any]:
        """根据 Git Diff 给出的文件清单做增量同步。

        - 删除受影响文件下的旧 Function / CALLS 边
        - 重新解析这些文件并写入新节点 / 边
        - 不动 TestCase / TESTED_BY（手工映射）
        """
        start_ts = time.monotonic()
        py_files = [f for f in changed_files if f.endswith(".py")]
        if not py_files:
            return {"elapsed_seconds": 0.0, "files": 0, "skipped": True}

        self._progress("delete_old", 0.0)
        # 删除这些文件下的旧 Function 节点（DETACH 会同时删边）
        self.client.execute_write(
            "MATCH (f:Function) WHERE f.file_path IN $files DETACH DELETE f",
            {"files": py_files},
        )

        self._progress("scan_changed", 0.20)
        scan_result = self._scan_python_files(only=py_files)
        self._batch_upsert("Module", scan_result["modules"])
        self._batch_upsert("Class", scan_result["classes"])
        self._batch_upsert("Function", scan_result["functions"])
        self._build_contains(scan_result["contains_edges"])
        self._build_calls(
            scan_result["call_edges"],
            function_signatures={n["id"] for n in scan_result["functions"]},
        )

        self._progress("done", 1.0)
        elapsed = time.monotonic() - start_ts
        stats = {
            "elapsed_seconds": round(elapsed, 2),
            "files": len(py_files),
            "function_count": len(scan_result["functions"]),
            "call_edge_count": len(scan_result["call_edges"]),
        }
        logger.info("Incremental sync done in %.2fs: %s", elapsed, stats)
        return stats

    # ------------------------------------------------------------------
    # 扫描内部实现
    # ------------------------------------------------------------------
    def _scan_python_files(self, only: list[str] | None = None) -> dict[str, list]:
        """单次遍历提取所有 Function / Class / Module / CALLS / CONTAINS。

        Args:
            only: 若给定，仅扫描这些相对路径（用于增量同步）。
        """
        from .ast_analyzer import ASTAnalyzer

        analyzer = ASTAnalyzer(str(self.repo_path))
        function_nodes: list[dict[str, Any]] = []
        class_nodes: dict[str, dict[str, Any]] = {}
        module_nodes: dict[str, dict[str, Any]] = {}
        contains_edges: list[dict[str, Any]] = []
        call_edges: list[dict[str, Any]] = []

        _SKIP_DIRS = {
            ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
            ".tox", ".pytest_cache", ".mypy_cache", "dist", "build",
            "site-packages", "pip", "playwright-report", "test-results",
            ".claude", ".idea", ".vscode", "htmlcov", "coverage_html",
        }

        def _should_skip(path: Path) -> bool:
            """跳过常见非项目目录。"""
            return any(part in _SKIP_DIRS for part in path.parts)

        if only is not None:
            iterator: Iterable[Path] = (self.repo_path / p for p in only)
        else:
            iterator = self.repo_path.rglob("*.py")

        for py_file in iterator:
            if not py_file.exists() or not py_file.is_file():
                continue
            if _should_skip(py_file):
                continue
            try:
                rel_path = str(py_file.relative_to(self.repo_path)).replace("\\", "/")
            except ValueError:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            funcs = analyzer._extract_functions(source, rel_path)
            if not funcs:
                continue

            module_dotted = funcs[0].get("module") or _module_dotted_from_path(rel_path)
            module_id = module_dotted
            module_nodes.setdefault(module_id, {
                "id": module_id,
                "name": module_dotted.split(".")[-1] if module_dotted else rel_path,
                "file_path": rel_path,
            })

            for f in funcs:
                fn_node = {
                    "id": f["signature"],
                    "name": f["name"],
                    "file_path": f["file"],
                    "module": f.get("module") or module_dotted,
                    "class_name": f.get("class_name") or "",
                    "qualified_name": f.get("qualified_name") or f["name"],
                    "start_line": f["start_line"],
                    "end_line": f["end_line"],
                    "signature": f["signature"],
                }
                function_nodes.append(fn_node)

                # Class 节点 + Class→Function CONTAINS
                class_name = f.get("class_name") or ""
                if class_name:
                    class_id = f"{module_dotted}:{class_name}"
                    class_nodes.setdefault(class_id, {
                        "id": class_id,
                        "name": class_name.split(".")[-1],
                        "qualified_name": class_name,
                        "module": module_dotted,
                        "file_path": rel_path,
                    })
                    contains_edges.append({
                        "from_id": class_id,
                        "to_id": f["signature"],
                        "from_label": "Class",
                        "to_label": "Function",
                    })
                    contains_edges.append({
                        "from_id": module_id,
                        "to_id": class_id,
                        "from_label": "Module",
                        "to_label": "Class",
                    })
                else:
                    contains_edges.append({
                        "from_id": module_id,
                        "to_id": f["signature"],
                        "from_label": "Module",
                        "to_label": "Function",
                    })

            # CALLS 边
            try:
                edges = analyzer.extract_call_edges(rel_path)
            except Exception as exc:  # pragma: no cover - 异常 AST 兜底
                logger.debug("extract_call_edges failed for %s: %s", rel_path, exc)
                edges = []
            for edge in edges:
                call_edges.append({
                    "caller_signature": edge.caller_signature,
                    "callee_name": edge.callee_name,
                    "callee_module": edge.callee_module,
                    "line": edge.line,
                })

        return {
            "functions": function_nodes,
            "classes": list(class_nodes.values()),
            "modules": list(module_nodes.values()),
            "contains_edges": contains_edges,
            "call_edges": call_edges,
        }

    def _scan_testcases(self) -> list[dict[str, Any]]:
        """从 Django ORM 导入 TestCase 节点。"""
        from apps.testcases.models import TestCase

        return [{
            "id": str(tc.id),
            "title": tc.title,
            "test_type": tc.test_type,
            "priority": tc.priority,
        } for tc in TestCase.objects.only(
            "id", "title", "test_type", "priority"
        ).iterator()]

    def _build_tested_by_relationships(self) -> None:
        """根据 TestCaseCodeMapping 建立 TESTED_BY 关系。"""
        from .models import TestCaseCodeMapping

        rels: list[dict[str, Any]] = []
        for mapping in TestCaseCodeMapping.objects.select_related("testcase").iterator():
            rels.append({
                "from_id": mapping.function_signature,
                "to_id": str(mapping.testcase.id),
                "properties": {
                    "confidence": mapping.confidence,
                    "type": mapping.mapping_type,
                },
            })
            if len(rels) >= self.batch_size:
                self._batch_create_rels(
                    "Function", "id", "TESTED_BY", "TestCase", "id", rels
                )
                rels = []
        if rels:
            self._batch_create_rels(
                "Function", "id", "TESTED_BY", "TestCase", "id", rels
            )

    def _build_contains(self, contains_edges: list[dict[str, Any]]) -> None:
        """根据 (from_label, to_label) 分桶后批量写入 CONTAINS。"""
        if not contains_edges:
            return
        buckets: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for edge in contains_edges:
            key = (edge["from_label"], edge["to_label"])
            buckets.setdefault(key, []).append({
                "from_id": edge["from_id"],
                "to_id": edge["to_id"],
            })
        for (from_label, to_label), rels in buckets.items():
            self._batch_create_rels(from_label, "id", "CONTAINS", to_label, "id", rels)

    def _build_calls(
        self, call_edges: list[dict[str, Any]], function_signatures: set[str]
    ) -> None:
        """将 CallEdge 解析结果转化为 Function→Function 的 CALLS 关系。

        策略：
        1. 若 callee_module + callee_name 能拼出 known signature → 直接连边
        2. 否则只按 callee_name 在已知 signature 中匹配（best-effort）
        """
        if not call_edges:
            return
        # 构造 name → [signatures] 索引
        name_index: dict[str, list[str]] = {}
        for sig in function_signatures:
            base_name = sig.split(":")[-1].split(".")[-1]
            name_index.setdefault(base_name, []).append(sig)

        rels: list[dict[str, Any]] = []
        for edge in call_edges:
            caller = edge["caller_signature"]
            if caller not in function_signatures:
                continue
            target_sig = self._resolve_callee(edge, function_signatures, name_index)
            if not target_sig or target_sig == caller:
                continue
            rels.append({
                "from_id": caller,
                "to_id": target_sig,
                "properties": {"line": edge["line"]},
            })
            if len(rels) >= self.batch_size:
                self._batch_create_rels(
                    "Function", "id", "CALLS", "Function", "id", rels
                )
                rels = []
        if rels:
            self._batch_create_rels(
                "Function", "id", "CALLS", "Function", "id", rels
            )

    @staticmethod
    def _resolve_callee(
        edge: dict[str, Any],
        signatures: set[str],
        name_index: dict[str, list[str]],
    ) -> str | None:
        """尝试把 (callee_name, callee_module) 解析为 known signature。"""
        callee_name = edge["callee_name"]
        callee_module = edge.get("callee_module")
        # 路径 1：精确拼接
        if callee_module:
            candidate = f"{callee_module}:{callee_name}"
            if candidate in signatures:
                return candidate
            # callee_name 可能是 obj.method，取最后一段
            short = callee_name.split(".")[-1]
            candidate2 = f"{callee_module}:{short}"
            if candidate2 in signatures:
                return candidate2
        # 路径 2：按短名称回查（仅当唯一匹配时）
        short = callee_name.split(".")[-1]
        candidates = name_index.get(short, [])
        if len(candidates) == 1:
            return candidates[0]
        return None

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------
    def _scan_api_endpoints(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """通过静态 URLConf 解析得到 ``(APIEndpoint 节点, APIEndpoint→Function HANDLES 关系)``。"""
        from .route_parser import DRFRouteParser

        urlconf = getattr(settings, "ROOT_URLCONF", "")
        if not urlconf:
            logger.debug("ROOT_URLCONF 未配置，跳过 API endpoint 扫描")
            return [], []

        try:
            parser = DRFRouteParser(str(self.repo_path))
            routes = parser.parse(urlconf)
        except FileNotFoundError as exc:
            logger.warning("DRFRouteParser 初始化失败: %s", exc)
            return [], []
        except Exception as exc:  # pragma: no cover
            logger.warning("DRFRouteParser 解析失败: %s", exc)
            return [], []

        nodes: list[dict[str, Any]] = []
        handles: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for route in routes:
            endpoint_id = f"{route.http_method} /{route.url_pattern}"
            if endpoint_id not in seen_ids:
                nodes.append({
                    "id": endpoint_id,
                    "url_pattern": route.url_pattern,
                    "http_method": route.http_method,
                    "name": route.name or "",
                    "source": route.source,
                })
                seen_ids.add(endpoint_id)
            if route.function_signature:
                handles.append({
                    "from_id": endpoint_id,
                    "to_id": route.function_signature,
                    "properties": {"source": route.source},
                })
        logger.info("API endpoints discovered: %d (handles=%d)", len(nodes), len(handles))
        return nodes, handles

    # ------------------------------------------------------------------
    # 批量写入薄封装（带分片）
    # ------------------------------------------------------------------
    def _batch_upsert(self, label: str, nodes: list[dict[str, Any]]) -> None:
        if not nodes:
            return
        for i in range(0, len(nodes), self.batch_size):
            self.client.batch_upsert_nodes(label, nodes[i:i + self.batch_size], key="id")

    def _batch_create_rels(
        self,
        from_label: str,
        from_key: str,
        rel_type: str,
        to_label: str,
        to_key: str,
        rels: list[dict[str, Any]],
    ) -> None:
        if not rels:
            return
        for i in range(0, len(rels), self.batch_size):
            self.client.batch_create_relationships(
                from_label, from_key, rel_type, to_label, to_key,
                rels[i:i + self.batch_size],
            )


def _module_dotted_from_path(rel_path: str) -> str:
    """``apps/foo/bar.py`` → ``apps.foo.bar``"""
    cleaned = rel_path.replace("\\", "/").rstrip("/")
    if cleaned.endswith(".py"):
        cleaned = cleaned[:-3]
    if cleaned.endswith("/__init__"):
        cleaned = cleaned[: -len("/__init__")]
    return cleaned.replace("/", ".")
