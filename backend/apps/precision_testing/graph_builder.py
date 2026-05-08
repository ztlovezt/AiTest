"""图构建器 — 将 Django ORM 数据同步到 Neo4j"""
import logging
from pathlib import Path
from typing import Any

from django.conf import settings

from .neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)


class GraphBuilder:
    """扫描代码仓库,将函数/类/用例/API 节点及关系写入 Neo4j。"""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.client = get_neo4j_client()

    def build_full_graph(self) -> None:
        """全量重建图(会清空现有图数据)。"""
        logger.info("Starting full graph build for %s", self.repo_path)
        self.client.clear_graph()

        # Step 1: 扫描所有 Python 文件,创建 Function/Class 节点
        function_nodes = self._scan_functions()
        self.client.batch_upsert_nodes("Function", function_nodes, key="id")

        # Step 2: 导入所有 TestCase 节点
        testcase_nodes = self._scan_testcases()
        self.client.batch_upsert_nodes("TestCase", testcase_nodes, key="id")

        # Step 3: 建立手工映射的 TESTED_BY 关系
        self._build_tested_by_relationships()

        # Step 4: API endpoint 节点 + HANDLES 关系
        api_nodes, api_handles = self._scan_api_endpoints()
        if api_nodes:
            self.client.batch_upsert_nodes("APIEndpoint", api_nodes, key="id")
        if api_handles:
            self.client.batch_create_relationships(
                "APIEndpoint", "id", "HANDLES", "Function", "id", api_handles
            )

        logger.info("Full graph build completed: %s", self.client.count_nodes())

    def _scan_functions(self) -> list[dict[str, Any]]:
        """扫描仓库所有 .py 文件,提取函数节点。"""
        from .ast_analyzer import ASTAnalyzer

        analyzer = ASTAnalyzer(str(self.repo_path))
        nodes = []
        for py_file in self.repo_path.rglob("*.py"):
            rel_path = str(py_file.relative_to(self.repo_path)).replace("\\", "/")
            try:
                source = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            funcs = analyzer._extract_functions(source, rel_path)
            nodes.extend([{
                "id": f["signature"],
                "name": f["name"],
                "file_path": f["file"],
                "start_line": f["start_line"],
                "end_line": f["end_line"],
                "signature": f["signature"],
            } for f in funcs])
        return nodes

    def _scan_testcases(self) -> list[dict[str, Any]]:
        """从 Django ORM 导入 TestCase 节点。"""
        from apps.testcases.models import TestCase

        return [{
            "id": str(tc.id),
            "title": tc.title,
            "test_type": tc.test_type,
            "priority": tc.priority,
        } for tc in TestCase.objects.only("id", "title", "test_type", "priority").iterator()]

    def _build_tested_by_relationships(self) -> None:
        """根据 TestCaseCodeMapping 建立 TESTED_BY 关系。"""
        from .models import TestCaseCodeMapping

        rels = []
        for mapping in TestCaseCodeMapping.objects.select_related("testcase").iterator():
            rels.append({
                "from_id": mapping.function_signature,
                "to_id": str(mapping.testcase.id),
                "properties": {"confidence": mapping.confidence, "type": mapping.mapping_type},
            })
            if len(rels) >= 500:
                self.client.batch_create_relationships(
                    "Function", "id", "TESTED_BY", "TestCase", "id", rels
                )
                rels = []
        if rels:
            self.client.batch_create_relationships(
                "Function", "id", "TESTED_BY", "TestCase", "id", rels
            )

    def _scan_api_endpoints(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """通过静态 URLConf 解析得到 ``(APIEndpoint 节点, APIEndpoint→Function HANDLES 关系)``。

        若 Django ROOT_URLCONF 未配置或解析失败,返回空。整个解析过程不执行
        用户代码,仅依赖 AST,因此可在 CI/沙箱安全运行。
        """
        from .route_parser import DRFRouteParser

        urlconf = getattr(settings, "ROOT_URLCONF", "")
        if not urlconf:
            logger.debug("ROOT_URLCONF 未配置,跳过 API endpoint 扫描")
            return [], []

        try:
            parser = DRFRouteParser(str(self.repo_path))
            routes = parser.parse(urlconf)
        except FileNotFoundError as exc:
            logger.warning("DRFRouteParser 初始化失败: %s", exc)
            return [], []

        nodes: list[dict[str, Any]] = []
        handles: list[dict[str, Any]] = []
        seen_endpoint_ids: set[str] = set()
        for route in routes:
            endpoint_id = f"{route.http_method} /{route.url_pattern}"
            if endpoint_id not in seen_endpoint_ids:
                nodes.append({
                    "id": endpoint_id,
                    "url_pattern": route.url_pattern,
                    "http_method": route.http_method,
                    "name": route.name or "",
                    "source": route.source,
                })
                seen_endpoint_ids.add(endpoint_id)
            if route.function_signature:
                handles.append({
                    "from_id": endpoint_id,
                    "to_id": route.function_signature,
                    "properties": {"source": route.source},
                })
        logger.info("API endpoints discovered: %d (handles=%d)", len(nodes), len(handles))
        return nodes, handles
