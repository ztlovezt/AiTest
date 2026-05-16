"""GraphBuilder 单元测试。

策略：
    * 纯函数 / 静态方法直接断言（_module_dotted_from_path / _iter_cypher_statements / _resolve_callee）
    * 依赖 Neo4j 客户端的 _batch_* / _build_* 通过桩客户端验证调用形态
    * 不启动 Django settings、不连真 Neo4j；仅覆盖算法层
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.precision_testing import graph_builder as gb_module
from apps.precision_testing.graph_builder import (
    GraphBuilder,
    _module_dotted_from_path,
)


# ----------------------------------------------------------------------
# Fake Neo4jClient
# ----------------------------------------------------------------------
class FakeClient:
    """记录每次 batch upsert / batch create rels 调用的桩。"""

    def __init__(self) -> None:
        self.upsert_calls: list[tuple[str, list[dict[str, Any]], str]] = []
        self.rel_calls: list[tuple[str, str, str, str, str, list[dict[str, Any]]]] = []
        self.write_calls: list[tuple[str, dict[str, Any]]] = []

    def batch_upsert_nodes(
        self, label: str, nodes: list[dict[str, Any]], key: str = "id"
    ) -> None:
        self.upsert_calls.append((label, list(nodes), key))

    def batch_create_relationships(
        self,
        from_label: str,
        from_key: str,
        rel_type: str,
        to_label: str,
        to_key: str,
        rels: list[dict[str, Any]],
    ) -> None:
        self.rel_calls.append(
            (from_label, from_key, rel_type, to_label, to_key, list(rels))
        )

    def execute_write(self, query: str, params: dict[str, Any] | None = None) -> list:
        self.write_calls.append((query, dict(params or {})))
        return []

    def clear_graph(self) -> None:  # pragma: no cover - 未在测试中调用
        pass

    def count_nodes(self) -> dict[str, int]:  # pragma: no cover
        return {}


@pytest.fixture
def builder(tmp_path, monkeypatch) -> GraphBuilder:
    client = FakeClient()
    monkeypatch.setattr(gb_module, "get_neo4j_client", lambda: client)
    inst = GraphBuilder(str(tmp_path), batch_size=2)
    inst.client = client  # 显式持有，便于断言
    return inst


# ----------------------------------------------------------------------
# 纯函数：_module_dotted_from_path
# ----------------------------------------------------------------------
class TestModuleDottedFromPath:
    @pytest.mark.parametrize(
        "given,expected",
        [
            ("apps/foo/bar.py", "apps.foo.bar"),
            ("apps\\foo\\bar.py", "apps.foo.bar"),  # Windows 路径
            ("apps/foo/__init__.py", "apps.foo"),
            ("foo.py", "foo"),
            ("apps/", "apps"),
            ("apps/foo/", "apps.foo"),
        ],
    )
    def test_paths_to_dotted(self, given: str, expected: str) -> None:
        assert _module_dotted_from_path(given) == expected


# ----------------------------------------------------------------------
# 静态方法：_iter_cypher_statements
# ----------------------------------------------------------------------
class TestIterCypherStatements:
    def test_splits_by_semicolon_and_strips_comments(self) -> None:
        text = (
            "// 创建约束\n"
            "CREATE CONSTRAINT fn_id IF NOT EXISTS\n"
            "FOR (f:Function) REQUIRE f.id IS UNIQUE;\n"
            "\n"
            "// 索引\n"
            "CREATE INDEX fn_module IF NOT EXISTS FOR (f:Function) ON (f.module);\n"
        )
        statements = list(GraphBuilder._iter_cypher_statements(text))
        assert len(statements) == 2
        assert "CREATE CONSTRAINT fn_id" in statements[0]
        assert "CREATE INDEX fn_module" in statements[1]
        for stmt in statements:
            assert "//" not in stmt

    def test_ignores_blank_statements(self) -> None:
        text = ";\n\n;\n  \n;\nCREATE INDEX foo IF NOT EXISTS FOR (x:X) ON (x.y);\n"
        statements = list(GraphBuilder._iter_cypher_statements(text))
        assert statements == [
            "CREATE INDEX foo IF NOT EXISTS FOR (x:X) ON (x.y)"
        ]

    def test_only_comment_block_yields_nothing(self) -> None:
        text = "// comment 1\n// comment 2\n"
        assert list(GraphBuilder._iter_cypher_statements(text)) == []


# ----------------------------------------------------------------------
# 静态方法：_resolve_callee
# ----------------------------------------------------------------------
class TestResolveCallee:
    @pytest.fixture
    def signatures(self) -> set[str]:
        return {
            "apps.foo:bar",
            "apps.foo:Klass.method",
            "apps.bar:unique_helper",
        }

    @pytest.fixture
    def name_index(self, signatures: set[str]) -> dict[str, list[str]]:
        idx: dict[str, list[str]] = {}
        for sig in signatures:
            base = sig.split(":")[-1].split(".")[-1]
            idx.setdefault(base, []).append(sig)
        return idx

    def test_exact_match_with_module(self, signatures, name_index) -> None:
        edge = {"callee_name": "bar", "callee_module": "apps.foo"}
        assert GraphBuilder._resolve_callee(edge, signatures, name_index) == "apps.foo:bar"

    def test_method_dotted_name_short_form(self, signatures, name_index) -> None:
        edge = {"callee_name": "Klass.method", "callee_module": "apps.foo"}
        assert (
            GraphBuilder._resolve_callee(edge, signatures, name_index)
            == "apps.foo:Klass.method"
        )

    def test_unique_short_name_fallback(self, signatures, name_index) -> None:
        edge = {"callee_name": "unique_helper", "callee_module": None}
        assert (
            GraphBuilder._resolve_callee(edge, signatures, name_index)
            == "apps.bar:unique_helper"
        )

    def test_ambiguous_short_name_returns_none(
        self, signatures: set[str], name_index: dict[str, list[str]]
    ) -> None:
        # 添加另一个同名 bar 让短名歧义
        signatures = signatures | {"apps.other:bar"}
        name_index = dict(name_index)
        name_index["bar"] = ["apps.foo:bar", "apps.other:bar"]
        edge = {"callee_name": "bar", "callee_module": None}
        assert GraphBuilder._resolve_callee(edge, signatures, name_index) is None

    def test_unknown_callee_returns_none(self, signatures, name_index) -> None:
        edge = {"callee_name": "nobody", "callee_module": "apps.ghost"}
        assert GraphBuilder._resolve_callee(edge, signatures, name_index) is None


# ----------------------------------------------------------------------
# _batch_upsert / _batch_create_rels 分片
# ----------------------------------------------------------------------
class TestBatching:
    def test_batch_upsert_chunks_by_batch_size(self, builder: GraphBuilder) -> None:
        nodes = [{"id": f"n{i}"} for i in range(5)]
        builder._batch_upsert("Function", nodes)
        # batch_size = 2 → 3 个分片 (2,2,1)
        assert len(builder.client.upsert_calls) == 3
        sizes = [len(call[1]) for call in builder.client.upsert_calls]
        assert sizes == [2, 2, 1]
        for label, _, key in builder.client.upsert_calls:
            assert label == "Function"
            assert key == "id"

    def test_batch_upsert_empty_is_noop(self, builder: GraphBuilder) -> None:
        builder._batch_upsert("Function", [])
        assert builder.client.upsert_calls == []

    def test_batch_create_rels_chunks(self, builder: GraphBuilder) -> None:
        rels = [{"from_id": f"a{i}", "to_id": f"b{i}"} for i in range(3)]
        builder._batch_create_rels("Function", "id", "CALLS", "Function", "id", rels)
        assert len(builder.client.rel_calls) == 2  # 2,1
        first = builder.client.rel_calls[0]
        assert first[0:5] == ("Function", "id", "CALLS", "Function", "id")
        assert len(first[5]) == 2


# ----------------------------------------------------------------------
# _build_calls 集成
# ----------------------------------------------------------------------
class TestBuildCalls:
    def test_unknown_caller_skipped(self, builder: GraphBuilder) -> None:
        edges = [
            {
                "caller_signature": "apps.x:ghost",  # 未在 signatures 集合中
                "callee_name": "bar",
                "callee_module": "apps.foo",
                "line": 1,
            }
        ]
        builder._build_calls(edges, function_signatures={"apps.foo:bar"})
        assert builder.client.rel_calls == []

    def test_self_call_skipped(self, builder: GraphBuilder) -> None:
        sigs = {"apps.foo:bar"}
        edges = [
            {
                "caller_signature": "apps.foo:bar",
                "callee_name": "bar",
                "callee_module": "apps.foo",
                "line": 7,
            }
        ]
        builder._build_calls(edges, function_signatures=sigs)
        assert builder.client.rel_calls == []

    def test_resolved_call_emits_rel(self, builder: GraphBuilder) -> None:
        sigs = {"apps.foo:bar", "apps.foo:caller"}
        edges = [
            {
                "caller_signature": "apps.foo:caller",
                "callee_name": "bar",
                "callee_module": "apps.foo",
                "line": 11,
            }
        ]
        builder._build_calls(edges, function_signatures=sigs)
        assert len(builder.client.rel_calls) == 1
        from_label, from_key, rel_type, to_label, to_key, rels = (
            builder.client.rel_calls[0]
        )
        assert (from_label, rel_type, to_label) == ("Function", "CALLS", "Function")
        assert rels == [
            {
                "from_id": "apps.foo:caller",
                "to_id": "apps.foo:bar",
                "properties": {"line": 11},
            }
        ]

    def test_empty_edges_is_noop(self, builder: GraphBuilder) -> None:
        builder._build_calls([], function_signatures={"a"})
        assert builder.client.rel_calls == []


# ----------------------------------------------------------------------
# _build_contains 分桶
# ----------------------------------------------------------------------
class TestBuildContains:
    def test_buckets_by_label_pair(self, builder: GraphBuilder) -> None:
        edges = [
            {
                "from_label": "Module",
                "to_label": "Class",
                "from_id": "m1",
                "to_id": "c1",
            },
            {
                "from_label": "Module",
                "to_label": "Class",
                "from_id": "m1",
                "to_id": "c2",
            },
            {
                "from_label": "Class",
                "to_label": "Function",
                "from_id": "c1",
                "to_id": "fn1",
            },
        ]
        builder._build_contains(edges)
        bucket_keys = {(c[0], c[3]) for c in builder.client.rel_calls}
        assert bucket_keys == {("Module", "Class"), ("Class", "Function")}
        for from_label, _, rel_type, to_label, _, rels in builder.client.rel_calls:
            assert rel_type == "CONTAINS"
            for rel in rels:
                assert set(rel.keys()) == {"from_id", "to_id"}

    def test_empty_edges_is_noop(self, builder: GraphBuilder) -> None:
        builder._build_contains([])
        assert builder.client.rel_calls == []
