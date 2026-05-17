"""影响传播查询 — 基于 Neo4j Cypher 的精准回归选取

Week 3 核心模块：
- 给定变更函数集，沿 CALLS 关系做 N 层广度传播
- 拉取受影响函数的 TESTED_BY 用例集合 → 最小回归集
- 反向推导 APIEndpoint：哪些 endpoint 受到这次变更影响
- 提供子图查询接口供 Cytoscape.js 前端可视化

性能目标：3 层影响传播 < 500 ms（中型仓库 ~10k 函数 / ~30k 调用边）
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .neo4j_client import get_neo4j_client

logger = logging.getLogger(__name__)


DEFAULT_DEPTH = 3
MAX_DEPTH = 8  # 防御性上限，避免误传过大深度导致 Neo4j 全图扫描


@dataclass
class ImpactResult:
    """影响传播查询结果。"""
    changed_functions: list[str]
    impacted_functions: list[str]
    impacted_testcases: list[str]
    impacted_endpoints: list[str]
    depth: int
    elapsed_ms: float
    propagation_paths: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_functions": self.changed_functions,
            "impacted_functions": self.impacted_functions,
            "impacted_testcases": self.impacted_testcases,
            "impacted_endpoints": self.impacted_endpoints,
            "depth": self.depth,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "propagation_paths": self.propagation_paths,
        }


class ImpactQuery:
    """影响传播查询门面，所有 Cypher 集中在此。"""

    def __init__(self) -> None:
        self.client = get_neo4j_client()

    # ------------------------------------------------------------------
    # 核心：影响传播
    # ------------------------------------------------------------------
    def query_impact(
        self,
        changed_function_ids: list[str],
        depth: int = DEFAULT_DEPTH,
        *,
        include_paths: bool = False,
    ) -> ImpactResult:
        """从变更函数出发，沿 CALLS 反向（被谁调用）做 ``depth`` 层传播。

        注意 CALLS 边方向：``A -[:CALLS]-> B`` 表示 A 调用 B。
        变更 B 时受影响的是 *上游* 调用方 A，因此查询走 ``<-[:CALLS]-`` 反向。

        Args:
            changed_function_ids: 变更函数 signature 列表（支持短名称，自动解析为完整签名）
            depth: 传播深度（默认 3，最大 8）
            include_paths: 是否返回每条传播路径（用于前端高亮，会增加 ~30% 耗时）
        """
        if not changed_function_ids:
            return ImpactResult([], [], [], [], depth, 0.0)
        depth = max(1, min(int(depth), MAX_DEPTH))

        # 将短名称（如 "ASTAnalyzer.__init__"）解析为完整签名
        changed_function_ids = self._resolve_function_ids(changed_function_ids)

        start = time.monotonic()
        impacted = self._query_impacted_functions(changed_function_ids, depth)
        # 把变更函数自身也并入受影响集合，方便回归用例选取
        all_function_ids = list(set(impacted) | set(changed_function_ids))

        testcases = self._query_testcases_for_functions(all_function_ids)
        endpoints = self._query_endpoints_for_functions(all_function_ids)

        paths: list[dict[str, Any]] = []
        if include_paths:
            paths = self._query_propagation_paths(changed_function_ids, depth)

        elapsed_ms = (time.monotonic() - start) * 1000
        result = ImpactResult(
            changed_functions=list(changed_function_ids),
            impacted_functions=impacted,
            impacted_testcases=testcases,
            impacted_endpoints=endpoints,
            depth=depth,
            elapsed_ms=elapsed_ms,
            propagation_paths=paths,
        )
        logger.info(
            "Impact query (depth=%d): changed=%d impacted=%d tcs=%d endpoints=%d in %.1fms",
            depth, len(changed_function_ids), len(impacted),
            len(testcases), len(endpoints), elapsed_ms,
        )
        return result

    # ------------------------------------------------------------------
    # 名称解析：将前端短名称映射为 Neo4j 完整签名
    # ------------------------------------------------------------------
    def _resolve_function_ids(self, function_ids: list[str]) -> list[str]:
        """将可能的短名称（如 ``ASTAnalyzer.__init__``）解析为完整签名。

        策略：
        1. 已包含 ``:`` 且包含 ``.`` 的视为完整签名，直接保留。
        2. 否则在 Neo4j 中按 ``name``、``qualified_name``、``id`` 模糊匹配。
        3. 唯一匹配时替换，无匹配或多匹配时保留原值（让查询自然返回空，前端可提示）。
        """
        resolved: list[str] = []
        for fid in function_ids:
            # 简单启发：包含模块分隔符且不以 .py 结尾的视为完整签名
            module_part = fid.split(":", 1)[0] if ":" in fid else ""
            if ":" in fid and "." in module_part and not module_part.endswith(".py"):
                resolved.append(fid)
                continue
            # 模糊匹配：支持 file.py:Class.method → 提取 Class.method
            short = fid
            suffix = f":{fid}"
            if ".py:" in fid:
                short = fid.split(".py:", 1)[1]
                suffix = f":{short}"
            records = self.client.execute_read(
                "MATCH (f:Function) WHERE f.name = $short "
                "OR f.qualified_name = $short "
                "OR f.id ENDS WITH $suffix "
                "RETURN f.id AS id LIMIT 5",
                {"short": short, "suffix": suffix},
            )
            if len(records) == 1:
                resolved.append(records[0]["id"])
            elif len(records) > 1:
                # 多个匹配，取第一个并记录警告
                logger.warning(
                    "Function short name '%s' matched %d signatures, using first: %s",
                    fid, len(records), records[0]["id"],
                )
                resolved.append(records[0]["id"])
            else:
                # 无匹配，保留原值
                resolved.append(fid)
        return resolved

    # ------------------------------------------------------------------
    # 子图查询（用于 Cytoscape 可视化）
    # ------------------------------------------------------------------
    def query_subgraph(
        self,
        node_id: str,
        node_label: str = "Function",
        depth: int = 2,
        node_limit: int = 200,
    ) -> dict[str, Any]:
        """以单一节点为中心拉取 N 层邻域子图（供前端 Cytoscape.js 渲染）。"""
        depth = max(1, min(int(depth), MAX_DEPTH))
        node_label = _safe_label(node_label)
        query = (
            f"MATCH (center:{node_label} {{id: $node_id}}) "
            f"OPTIONAL MATCH p = (center)-[*1..{depth}]-(neighbor) "
            f"WITH center, COLLECT(DISTINCT neighbor)[..$limit] AS neighbors, "
            f"     COLLECT(DISTINCT p) AS paths "
            f"RETURN center, neighbors, paths"
        )
        records = self.client.execute_read(query, {"node_id": node_id, "limit": node_limit})
        if not records:
            return {"nodes": [], "edges": []}
        return _records_to_cytoscape(records)

    # ------------------------------------------------------------------
    # 内部 Cypher 调用
    # ------------------------------------------------------------------
    def _query_impacted_functions(
        self, changed_ids: list[str], depth: int
    ) -> list[str]:
        """变更函数的上游受影响调用方（不含自身）。"""
        query = (
            "MATCH (changed:Function) WHERE changed.id IN $changed_ids "
            f"OPTIONAL MATCH (caller:Function)-[:CALLS*1..{depth}]->(changed) "
            "WITH COLLECT(DISTINCT caller.id) AS caller_ids "
            "UNWIND caller_ids AS fid "
            "RETURN DISTINCT fid AS function_id"
        )
        records = self.client.execute_read(query, {"changed_ids": changed_ids})
        return [r["function_id"] for r in records if r.get("function_id")]

    def _query_testcases_for_functions(self, function_ids: list[str]) -> list[str]:
        if not function_ids:
            return []
        query = (
            "MATCH (f:Function)-[:TESTED_BY]->(tc:TestCase) "
            "WHERE f.id IN $ids "
            "RETURN DISTINCT tc.id AS testcase_id"
        )
        records = self.client.execute_read(query, {"ids": function_ids})
        return [r["testcase_id"] for r in records if r.get("testcase_id")]

    def _query_endpoints_for_functions(self, function_ids: list[str]) -> list[str]:
        if not function_ids:
            return []
        query = (
            "MATCH (ae:APIEndpoint)-[:HANDLES]->(f:Function) "
            "WHERE f.id IN $ids "
            "RETURN DISTINCT ae.id AS endpoint_id"
        )
        records = self.client.execute_read(query, {"ids": function_ids})
        return [r["endpoint_id"] for r in records if r.get("endpoint_id")]

    def _query_propagation_paths(
        self, changed_ids: list[str], depth: int
    ) -> list[dict[str, Any]]:
        """返回 caller -> ... -> changed 的传播路径（前端高亮用）。"""
        query = (
            "MATCH (changed:Function) WHERE changed.id IN $changed_ids "
            f"MATCH p = (caller:Function)-[:CALLS*1..{depth}]->(changed) "
            "RETURN [n IN nodes(p) | n.id] AS path_ids, length(p) AS hops "
            "ORDER BY hops ASC LIMIT 100"
        )
        records = self.client.execute_read(query, {"changed_ids": changed_ids})
        return [
            {"path": r["path_ids"], "hops": r["hops"]}
            for r in records if r.get("path_ids")
        ]

    # ------------------------------------------------------------------
    # 全图采样（供 GraphDataView 概览模式）
    # ------------------------------------------------------------------
    def build_impact_graph_data(self, result: ImpactResult) -> dict[str, Any]:
        """根据 ImpactResult 构建 Cytoscape 格式的 graph data。

        包含所有 changed/impacted functions、impacted testcases
        以及它们之间的关系（CALLS / TESTED_BY / HANDLES）。
        """
        all_function_ids = list(
            set(result.changed_functions) | set(result.impacted_functions)
        )
        all_testcase_ids = list(set(result.impacted_testcases))

        if not all_function_ids and not all_testcase_ids:
            return {"nodes": [], "edges": []}

        node_records: list[dict[str, Any]] = []
        if all_function_ids:
            func_records = self.client.execute_read(
                "MATCH (f:Function) WHERE f.id IN $ids "
                "RETURN id(f) AS internal_id, labels(f) AS labels, f AS props",
                {"ids": all_function_ids},
            )
            node_records.extend(func_records)

        if all_testcase_ids:
            tc_records = self.client.execute_read(
                "MATCH (tc:TestCase) WHERE tc.id IN $ids "
                "RETURN id(tc) AS internal_id, labels(tc) AS labels, tc AS props",
                {"ids": all_testcase_ids},
            )
            node_records.extend(tc_records)

        node_ids = [r["internal_id"] for r in node_records]

        edge_records: list[dict[str, Any]] = []
        if len(node_ids) > 1:
            edge_records = self.client.execute_read(
                "MATCH (a)-[r]->(b) "
                "WHERE id(a) IN $node_ids AND id(b) IN $node_ids "
                "RETURN id(a) AS source, id(b) AS target, type(r) AS rel_type, "
                "       properties(r) AS rel_props",
                {"node_ids": node_ids},
            )

        cy_data = _records_to_cytoscape_simple(node_records, edge_records)

        # 标记变更函数，方便前端高亮
        changed_set = set(result.changed_functions)
        for node in cy_data["nodes"]:
            if node["data"].get("node_id") in changed_set:
                node["data"]["is_changed"] = True

        return cy_data

    def query_overview(
        self, node_type: str | None = None, limit: int = 200
    ) -> dict[str, Any]:
        """拉一个全图采样切片，按节点类型过滤，返回 Cytoscape 格式。"""
        if node_type:
            label = _safe_label(node_type)
            node_query = (
                f"MATCH (n:{label}) "
                "RETURN labels(n) AS labels, n AS props, id(n) AS internal_id "
                "LIMIT $limit"
            )
        else:
            node_query = (
                "MATCH (n) "
                "RETURN labels(n) AS labels, n AS props, id(n) AS internal_id "
                "LIMIT $limit"
            )
        edge_query = (
            "MATCH (a)-[r]->(b) "
            "WHERE id(a) IN $node_ids AND id(b) IN $node_ids "
            "RETURN id(a) AS source, id(b) AS target, type(r) AS rel_type, "
            "       properties(r) AS rel_props"
        )
        node_records = self.client.execute_read(node_query, {"limit": limit})
        node_ids = [r["internal_id"] for r in node_records]
        edge_records = (
            self.client.execute_read(edge_query, {"node_ids": node_ids})
            if node_ids else []
        )
        return _records_to_cytoscape_simple(node_records, edge_records)


# ----------------------------------------------------------------------
# Cytoscape.js 兼容序列化
# ----------------------------------------------------------------------
_VALID_LABEL = {"Function", "Class", "Module", "TestCase", "APIEndpoint"}


def _safe_label(label: str) -> str:
    """白名单校验，防止 Cypher 标签注入。"""
    if label not in _VALID_LABEL:
        raise ValueError(f"未知节点类型: {label!r}; 允许 {sorted(_VALID_LABEL)}")
    return label


def _node_dict(internal_id: int, labels: list[str], props: dict[str, Any]) -> dict[str, Any]:
    label = labels[0] if labels else "Unknown"
    name = (
        props.get("name")
        or props.get("title")
        or props.get("qualified_name")
        or props.get("id")
        or str(internal_id)
    )
    # 注意：props 里的 "id" 是节点业务 id（如 ``apps.foo:bar``），不能覆盖
    # Cytoscape 用作端点引用的 ``data.id``（必须等于 Neo4j 内部 id）。
    extra_props = {
        k: v for k, v in props.items() if k not in {"name", "title", "id"}
    }
    return {
        "data": {
            "id": str(internal_id),
            "label": label,
            "name": name,
            "node_type": label,
            "node_id": props.get("id", ""),
            **extra_props,
        },
        "classes": label.lower(),
    }


def _edge_dict(source: int, target: int, rel_type: str, props: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "data": {
            "id": f"e{source}-{target}-{rel_type}",
            "source": str(source),
            "target": str(target),
            "label": rel_type,
            "rel_type": rel_type,
            **(props or {}),
        },
        "classes": rel_type.lower(),
    }


def _records_to_cytoscape_simple(
    node_records: list[dict[str, Any]],
    edge_records: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = []
    for r in node_records:
        props = dict(r.get("props") or {})
        nodes.append(_node_dict(r["internal_id"], r.get("labels") or [], props))
    edges = [
        _edge_dict(r["source"], r["target"], r["rel_type"], r.get("rel_props"))
        for r in edge_records
    ]
    return {"nodes": nodes, "edges": edges}


def _records_to_cytoscape(records: list[dict[str, Any]]) -> dict[str, Any]:
    """子图查询结果（含 paths）转 Cytoscape。"""
    seen_nodes: dict[int, dict[str, Any]] = {}
    seen_edges: dict[str, dict[str, Any]] = {}

    def _add_node(node_obj: Any) -> None:
        if node_obj is None:
            return
        internal_id = node_obj.element_id if hasattr(node_obj, "element_id") else None
        # neo4j Node 实现了 dict-like 访问
        try:
            internal_id_int = int(node_obj.id)  # type: ignore[attr-defined]
        except (AttributeError, TypeError, ValueError):
            internal_id_int = hash(internal_id or id(node_obj))
        if internal_id_int in seen_nodes:
            return
        labels = list(getattr(node_obj, "labels", []) or [])
        props = dict(node_obj)
        seen_nodes[internal_id_int] = _node_dict(internal_id_int, labels, props)

    def _add_rel(rel_obj: Any) -> None:
        if rel_obj is None:
            return
        try:
            src = int(rel_obj.start_node.id)  # type: ignore[attr-defined]
            tgt = int(rel_obj.end_node.id)    # type: ignore[attr-defined]
            rel_type = rel_obj.type           # type: ignore[attr-defined]
        except AttributeError:
            return
        key = f"{src}-{tgt}-{rel_type}"
        if key in seen_edges:
            return
        seen_edges[key] = _edge_dict(src, tgt, rel_type, dict(rel_obj))

    for record in records:
        _add_node(record.get("center"))
        for n in record.get("neighbors") or []:
            _add_node(n)
        for path in record.get("paths") or []:
            if path is None:
                continue
            for n in getattr(path, "nodes", []) or []:
                _add_node(n)
            for r in getattr(path, "relationships", []) or []:
                _add_rel(r)
    return {"nodes": list(seen_nodes.values()), "edges": list(seen_edges.values())}


def get_impact_query() -> ImpactQuery:
    """工厂函数。"""
    return ImpactQuery()
