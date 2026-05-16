"""Neo4j 图数据库客户端单例

提供统一的 Bolt 连接池管理,支持图模型 CRUD 和批量写入。
"""
from __future__ import annotations

import logging
from typing import Any, Iterator

from django.conf import settings
from neo4j import GraphDatabase, Driver

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 单例客户端"""
    _instance: Neo4jClient | None = None
    _driver: Driver | None = None

    def __new__(cls) -> Neo4jClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
            user = getattr(settings, "NEO4J_USER", "neo4j")
            password = getattr(settings, "NEO4J_PASSWORD", "testhub")
            self._driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
        return self._driver

    def verify_connectivity(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning("Neo4j connectivity check failed: %s", exc)
            return False

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    # ------------------------------------------------------------------
    # 底层会话封装
    # ------------------------------------------------------------------
    def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """执行只读 Cypher 查询,返回记录列表。"""
        with self.driver.session() as session:
            tx = session.begin_transaction()
            try:
                result = tx.run(query, parameters or {})
                records = [record.data() for record in result]
                tx.commit()
            finally:
                tx.close()
        return records

    def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """执行写操作 Cypher 查询。"""
        with self.driver.session() as session:
            tx = session.begin_transaction()
            try:
                result = tx.run(query, parameters or {})
                records = [record.data() for record in result]
                tx.commit()
            finally:
                tx.close()
        return records

    # ------------------------------------------------------------------
    # 批量写入(核心优化)
    # ------------------------------------------------------------------
    def batch_upsert_nodes(
        self, label: str, nodes: list[dict[str, Any]], key: str = "id"
    ) -> None:
        """使用 UNWIND 批量 MERGE 节点。

        Args:
            label: 节点标签,如 ``Function``、``TestCase``。
            nodes: 节点属性字典列表,每个字典必须包含 ``key`` 字段。
            key: 用于去重的属性名,默认 ``id``。
        """
        if not nodes:
            return
        query = (
            f"UNWIND $nodes AS node "
            f"MERGE (n:{label} {{{key}: node.{key}}}) "
            f"SET n += node"
        )
        self.execute_write(query, {"nodes": nodes})

    def batch_create_relationships(
        self,
        from_label: str,
        from_key: str,
        rel_type: str,
        to_label: str,
        to_key: str,
        rels: list[dict[str, Any]],
    ) -> None:
        """使用 UNWIND 批量创建关系。

        Args:
            rels: 每个元素必须包含 ``from_id``、``to_id``,可选 ``properties``。
        """
        if not rels:
            return
        query = (
            f"UNWIND $rels AS rel "
            f"MATCH (a:{from_label} {{{from_key}: rel.from_id}}), "
            f"      (b:{to_label} {{{to_key}: rel.to_id}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += COALESCE(rel.properties, {{}})"
        )
        self.execute_write(query, {"rels": rels})

    # ------------------------------------------------------------------
    # 图查询辅助
    # ------------------------------------------------------------------
    def get_tested_by(self, function_ids: list[str]) -> list[str]:
        """根据函数 ID 列表查询覆盖这些函数的测试用例 ID 列表。"""
        if not function_ids:
            return []
        query = (
            "MATCH (f:Function)-[:TESTED_BY]->(tc:TestCase) "
            "WHERE f.id IN $function_ids "
            "RETURN DISTINCT tc.id AS testcase_id"
        )
        records = self.execute_read(query, {"function_ids": function_ids})
        return [r["testcase_id"] for r in records]

    def get_impacted_functions(self, changed_function_ids: list[str]) -> list[str]:
        """通过 CALLS 关系递归查找受影响的函数(包含自身)。"""
        if not changed_function_ids:
            return []
        query = (
            "MATCH (f:Function) "
            "WHERE f.id IN $changed_ids "
            "OPTIONAL MATCH (f)-[:CALLS*1..5]->(dep:Function) "
            "WITH COLLECT(DISTINCT f.id) + COLLECT(DISTINCT dep.id) AS all_ids "
            "UNWIND all_ids AS fid "
            "RETURN DISTINCT fid AS function_id"
        )
        records = self.execute_read(query, {"changed_ids": changed_function_ids})
        return [r["function_id"] for r in records if r["function_id"]]

    def clear_graph(self) -> None:
        """清空整个图数据库(仅用于重建或测试)。"""
        self.execute_write("MATCH (n) DETACH DELETE n")

    def count_nodes(self) -> dict[str, int]:
        """统计各类节点数量。"""
        query = (
            "MATCH (n) "
            "RETURN labels(n)[0] AS label, count(n) AS cnt"
        )
        records = self.execute_read(query)
        return {r["label"]: r["cnt"] for r in records}


def get_neo4j_client() -> Neo4jClient:
    """获取 Neo4j 客户端实例(工厂函数)。"""
    return Neo4jClient()
