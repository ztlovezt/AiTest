"""ImpactQuery 单元测试。

覆盖目标：
    * 影响传播查询的 Cypher 形态与参数注入
    * 深度边界（<1, =3, >MAX_DEPTH）裁剪
    * 标签白名单 ``_safe_label``
    * Cytoscape 序列化（概览模式 + 子图模式）
    * ImpactResult 的 dataclass / to_dict 行为
    * 空输入快路径
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.precision_testing import impact_query as iq_module
from apps.precision_testing.impact_query import (
    DEFAULT_DEPTH,
    MAX_DEPTH,
    ImpactQuery,
    ImpactResult,
    _records_to_cytoscape_simple,
    _safe_label,
)


# ----------------------------------------------------------------------
# Stub Neo4jClient
# ----------------------------------------------------------------------
class FakeNeo4jClient:
    """记录调用并按顺序返回预设结果的 Neo4j 客户端伪实现。"""

    def __init__(self, read_results: list[list[dict[str, Any]]] | None = None) -> None:
        self._read_results = list(read_results or [])
        self.read_calls: list[tuple[str, dict[str, Any]]] = []
        self.write_calls: list[tuple[str, dict[str, Any]]] = []

    def execute_read(self, query: str, params: dict[str, Any] | None = None):
        self.read_calls.append((query, dict(params or {})))
        if not self._read_results:
            return []
        return self._read_results.pop(0)

    def execute_write(self, query: str, params: dict[str, Any] | None = None):
        self.write_calls.append((query, dict(params or {})))
        return []


@pytest.fixture
def fake_client(monkeypatch):
    """返回一个工厂：``fake_client(reads=[...])`` 装配后注入到 impact_query 模块。"""

    def _factory(reads: list[list[dict[str, Any]]] | None = None) -> FakeNeo4jClient:
        client = FakeNeo4jClient(read_results=reads)
        monkeypatch.setattr(iq_module, "get_neo4j_client", lambda: client)
        return client

    return _factory


# ----------------------------------------------------------------------
# _safe_label 白名单
# ----------------------------------------------------------------------
class TestSafeLabel:
    @pytest.mark.parametrize(
        "label", ["Function", "Class", "Module", "TestCase", "APIEndpoint"]
    )
    def test_valid_labels_pass_through(self, label: str) -> None:
        assert _safe_label(label) == label

    @pytest.mark.parametrize(
        "label",
        [
            "function",   # 大小写敏感
            "Foo",        # 未知
            "Function; DROP DATABASE",  # 注入尝试
            "",
        ],
    )
    def test_invalid_labels_raise(self, label: str) -> None:
        with pytest.raises(ValueError, match="未知节点类型"):
            _safe_label(label)


# ----------------------------------------------------------------------
# ImpactResult 数据类
# ----------------------------------------------------------------------
class TestImpactResult:
    def test_to_dict_round_trips_fields(self) -> None:
        result = ImpactResult(
            changed_functions=["a"],
            impacted_functions=["b", "c"],
            impacted_testcases=["tc1"],
            impacted_endpoints=["ep1"],
            depth=3,
            elapsed_ms=12.345,
        )
        payload = result.to_dict()
        assert payload["changed_functions"] == ["a"]
        assert payload["impacted_functions"] == ["b", "c"]
        assert payload["impacted_testcases"] == ["tc1"]
        assert payload["impacted_endpoints"] == ["ep1"]
        assert payload["depth"] == 3
        assert payload["elapsed_ms"] == 12.35  # 四舍五入到 2 位
        assert payload["propagation_paths"] == []

    def test_default_propagation_paths_is_empty(self) -> None:
        result = ImpactResult([], [], [], [], 1, 0.0)
        assert result.propagation_paths == []


# ----------------------------------------------------------------------
# ImpactQuery.query_impact 主流程
# ----------------------------------------------------------------------
class TestQueryImpact:
    def test_empty_changed_returns_empty_result_without_query(
        self, fake_client
    ) -> None:
        client = fake_client(reads=[])
        result = ImpactQuery().query_impact([])
        assert isinstance(result, ImpactResult)
        assert result.changed_functions == []
        assert result.impacted_functions == []
        assert result.impacted_testcases == []
        assert result.impacted_endpoints == []
        assert result.elapsed_ms == 0.0
        assert client.read_calls == []  # 空输入不触发查询

    def test_full_pipeline_collects_impacted_tcs_and_endpoints(
        self, fake_client
    ) -> None:
        client = fake_client(
            reads=[
                # _query_impacted_functions
                [
                    {"function_id": "apps.foo:caller_a"},
                    {"function_id": "apps.foo:caller_b"},
                    {"function_id": None},  # 应被过滤
                ],
                # _query_testcases_for_functions
                [{"testcase_id": "TC-1"}, {"testcase_id": "TC-2"}],
                # _query_endpoints_for_functions
                [{"endpoint_id": "GET /api/foo"}],
            ]
        )
        result = ImpactQuery().query_impact(
            ["apps.foo:changed"], depth=DEFAULT_DEPTH
        )
        assert set(result.impacted_functions) == {
            "apps.foo:caller_a",
            "apps.foo:caller_b",
        }
        assert result.impacted_testcases == ["TC-1", "TC-2"]
        assert result.impacted_endpoints == ["GET /api/foo"]
        assert result.depth == DEFAULT_DEPTH
        assert result.elapsed_ms >= 0.0

    def test_changed_functions_merged_into_testcase_lookup(
        self, fake_client
    ) -> None:
        client = fake_client(
            reads=[
                [{"function_id": "caller_a"}],     # impacted
                [{"testcase_id": "TC-1"}],         # testcases
                [],                                  # endpoints
            ]
        )
        ImpactQuery().query_impact(["changed_x"])

        # 第二次 read = testcase 查询，参数应当包含 changed + impacted
        tc_query, tc_params = client.read_calls[1]
        assert "TESTED_BY" in tc_query
        assert set(tc_params["ids"]) == {"caller_a", "changed_x"}

    @pytest.mark.parametrize(
        "given,expected",
        [
            (-5, 1),
            (0, 1),
            (1, 1),
            (3, 3),
            (MAX_DEPTH, MAX_DEPTH),
            (MAX_DEPTH + 100, MAX_DEPTH),
        ],
    )
    def test_depth_clamped_to_valid_range(
        self, fake_client, given: int, expected: int
    ) -> None:
        fake_client(reads=[[], [], []])
        result = ImpactQuery().query_impact(["changed"], depth=given)
        assert result.depth == expected

    def test_include_paths_triggers_extra_query(self, fake_client) -> None:
        client = fake_client(
            reads=[
                [],                                          # impacted
                [],                                          # testcases
                [],                                          # endpoints
                [{"path_ids": ["a", "b", "c"], "hops": 2}],  # paths
            ]
        )
        result = ImpactQuery().query_impact(
            ["x"], depth=2, include_paths=True
        )
        assert len(client.read_calls) == 4
        assert result.propagation_paths == [
            {"path": ["a", "b", "c"], "hops": 2}
        ]

    def test_skip_paths_avoids_extra_query(self, fake_client) -> None:
        client = fake_client(reads=[[], [], []])
        ImpactQuery().query_impact(["x"], include_paths=False)
        assert len(client.read_calls) == 3

    def test_cypher_uses_reverse_calls_traversal(self, fake_client) -> None:
        client = fake_client(reads=[[], [], []])
        ImpactQuery().query_impact(["fn"], depth=4)
        impacted_query, params = client.read_calls[0]
        assert "[:CALLS*1..4]->(changed)" in impacted_query  # 正向写法但 caller 在左
        assert "(caller:Function)" in impacted_query
        assert params["changed_ids"] == ["fn"]


# ----------------------------------------------------------------------
# ImpactQuery.query_subgraph
# ----------------------------------------------------------------------
class TestQuerySubgraph:
    def test_invalid_label_rejected(self, fake_client) -> None:
        fake_client(reads=[])
        with pytest.raises(ValueError):
            ImpactQuery().query_subgraph("id1", node_label="EvilLabel")

    def test_empty_records_returns_empty_payload(self, fake_client) -> None:
        fake_client(reads=[[]])
        payload = ImpactQuery().query_subgraph("fn1")
        assert payload == {"nodes": [], "edges": []}

    def test_label_and_depth_substituted(self, fake_client) -> None:
        client = fake_client(reads=[[]])
        ImpactQuery().query_subgraph("fn1", node_label="Class", depth=3)
        query, params = client.read_calls[0]
        assert "MATCH (center:Class" in query
        assert "[*1..3]" in query
        assert params["node_id"] == "fn1"

    def test_subgraph_depth_clamped(self, fake_client) -> None:
        client = fake_client(reads=[[]])
        ImpactQuery().query_subgraph("fn1", depth=MAX_DEPTH + 50)
        query, _ = client.read_calls[0]
        assert f"[*1..{MAX_DEPTH}]" in query


# ----------------------------------------------------------------------
# ImpactQuery.query_overview
# ----------------------------------------------------------------------
class TestQueryOverview:
    def test_overview_without_node_type(self, fake_client) -> None:
        client = fake_client(
            reads=[
                [
                    {
                        "labels": ["Function"],
                        "props": {"id": "fn1", "name": "fn1"},
                        "internal_id": 100,
                    }
                ],
                [
                    {
                        "source": 100,
                        "target": 200,
                        "rel_type": "CALLS",
                        "rel_props": {},
                    }
                ],
            ]
        )
        payload = ImpactQuery().query_overview(limit=50)
        assert payload["nodes"][0]["data"]["id"] == "100"
        assert payload["edges"][0]["data"]["rel_type"] == "CALLS"
        # edge 查询使用收集到的 node_ids
        edge_call = client.read_calls[1]
        assert edge_call[1]["node_ids"] == [100]

    def test_overview_with_node_type_uses_label_filter(self, fake_client) -> None:
        client = fake_client(reads=[[], []])
        ImpactQuery().query_overview(node_type="Function", limit=10)
        node_query, params = client.read_calls[0]
        assert "MATCH (n:Function)" in node_query
        assert params["limit"] == 10

    def test_overview_invalid_node_type(self, fake_client) -> None:
        fake_client(reads=[])
        with pytest.raises(ValueError):
            ImpactQuery().query_overview(node_type="NotALabel")

    def test_overview_skips_edge_query_when_no_nodes(self, fake_client) -> None:
        client = fake_client(reads=[[]])
        payload = ImpactQuery().query_overview()
        assert payload == {"nodes": [], "edges": []}
        assert len(client.read_calls) == 1


# ----------------------------------------------------------------------
# Cytoscape 序列化
# ----------------------------------------------------------------------
class TestCytoscapeSerialization:
    def test_records_to_cytoscape_simple_strips_known_aliases(self) -> None:
        node_records = [
            {
                "labels": ["Function"],
                "props": {
                    "id": "apps.foo:bar",
                    "name": "bar",
                    "title": "Bar",
                    "module": "apps.foo",
                },
                "internal_id": 7,
            }
        ]
        edge_records = [
            {"source": 7, "target": 9, "rel_type": "CALLS", "rel_props": {"weight": 1}}
        ]
        payload = _records_to_cytoscape_simple(node_records, edge_records)
        node = payload["nodes"][0]
        assert node["data"]["id"] == "7"
        assert node["data"]["label"] == "Function"
        assert node["data"]["name"] == "bar"
        assert node["classes"] == "function"
        # name/title 不应再出现在透传属性里（避免与显式 name 冲突）
        assert "title" not in node["data"]

        edge = payload["edges"][0]
        assert edge["data"]["source"] == "7"
        assert edge["data"]["target"] == "9"
        assert edge["data"]["weight"] == 1
        assert edge["classes"] == "calls"

    def test_unknown_label_falls_back_to_unknown(self) -> None:
        payload = _records_to_cytoscape_simple(
            [{"labels": [], "props": {"id": "x"}, "internal_id": 1}],
            [],
        )
        assert payload["nodes"][0]["data"]["label"] == "Unknown"


# ----------------------------------------------------------------------
# 子图模式 — _records_to_cytoscape 经由 query_subgraph
# ----------------------------------------------------------------------
class _StubNode:
    """模拟 neo4j.graph.Node 的极简对象。"""

    def __init__(self, *, internal_id: int, labels: list[str], props: dict[str, Any]) -> None:
        self.id = internal_id
        self.element_id = f"4:{internal_id}"
        self.labels = labels
        self._props = props

    def __iter__(self):
        return iter(self._props)

    def keys(self):
        return self._props.keys()

    def __getitem__(self, key):
        return self._props[key]


class _StubRel:
    def __init__(self, *, start: _StubNode, end: _StubNode, rel_type: str, props: dict[str, Any] | None = None) -> None:
        self.start_node = start
        self.end_node = end
        self.type = rel_type
        self._props = props or {}

    def __iter__(self):
        return iter(self._props)

    def keys(self):
        return self._props.keys()

    def __getitem__(self, key):
        return self._props[key]


class _StubPath:
    def __init__(self, nodes: list[_StubNode], rels: list[_StubRel]) -> None:
        self.nodes = nodes
        self.relationships = rels


class TestSubgraphCytoscape:
    def test_subgraph_with_records_serializes_nodes_and_edges(
        self, fake_client
    ) -> None:
        center = _StubNode(
            internal_id=10, labels=["Function"], props={"id": "fn1", "name": "fn1"}
        )
        neighbor = _StubNode(
            internal_id=11, labels=["Function"], props={"id": "fn2", "name": "fn2"}
        )
        rel = _StubRel(start=center, end=neighbor, rel_type="CALLS")
        path = _StubPath(nodes=[center, neighbor], rels=[rel])

        fake_client(
            reads=[
                [
                    {"center": center, "neighbors": [neighbor], "paths": [path]},
                ]
            ]
        )
        payload = ImpactQuery().query_subgraph("fn1", node_label="Function")
        node_ids = {n["data"]["id"] for n in payload["nodes"]}
        assert node_ids == {"10", "11"}
        edge = payload["edges"][0]
        assert edge["data"]["source"] == "10"
        assert edge["data"]["target"] == "11"
        assert edge["data"]["rel_type"] == "CALLS"

    def test_subgraph_dedupes_repeated_nodes_across_paths(
        self, fake_client
    ) -> None:
        center = _StubNode(
            internal_id=1, labels=["Function"], props={"id": "fn", "name": "fn"}
        )
        neighbor = _StubNode(
            internal_id=2, labels=["Function"], props={"id": "fn2"}
        )
        rel = _StubRel(start=center, end=neighbor, rel_type="CALLS")
        path = _StubPath(nodes=[center, neighbor], rels=[rel])

        # 两条记录引用相同节点 → 去重
        fake_client(
            reads=[
                [
                    {"center": center, "neighbors": [neighbor], "paths": [path]},
                    {"center": center, "neighbors": [neighbor], "paths": [path]},
                ]
            ]
        )
        payload = ImpactQuery().query_subgraph("fn")
        assert len(payload["nodes"]) == 2
        assert len(payload["edges"]) == 1


# ----------------------------------------------------------------------
# 工厂函数
# ----------------------------------------------------------------------
class TestFactory:
    def test_get_impact_query_returns_instance(self, fake_client) -> None:
        from apps.precision_testing.impact_query import get_impact_query

        fake_client(reads=[])
        instance = get_impact_query()
        assert isinstance(instance, ImpactQuery)


# ----------------------------------------------------------------------
# 内部方法直接调用 — 覆盖 empty-ids 早返回分支
# ----------------------------------------------------------------------
class TestInternalEmptyIds:
    def test_testcases_empty_ids_returns_empty(self, fake_client) -> None:
        client = fake_client(reads=[])
        result = ImpactQuery()._query_testcases_for_functions([])
        assert result == []
        assert client.read_calls == []

    def test_endpoints_empty_ids_returns_empty(self, fake_client) -> None:
        client = fake_client(reads=[])
        result = ImpactQuery()._query_endpoints_for_functions([])
        assert result == []
        assert client.read_calls == []
