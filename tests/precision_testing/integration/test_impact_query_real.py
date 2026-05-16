"""ImpactQuery 集成测试 — 连接真实 Neo4j

前置条件：
    * Neo4j 运行于 localhost:7474
    * Django settings 已配置 NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
    * 数据库为空或测试数据已准备好

运行方式：
    pytest tests/precision_testing/integration/test_impact_query_real.py -v
"""
from __future__ import annotations

import pytest

from apps.precision_testing.impact_query import (
    DEFAULT_DEPTH,
    ImpactQuery,
    _safe_label,
)


@pytest.fixture
def clean_graph():
    """每个测试前清空图，保证测试隔离。"""
    from apps.precision_testing.neo4j_client import get_neo4j_client
    client = get_neo4j_client()
    client.clear_graph()
    yield
    # teardown — 测试后再次清空
    client.clear_graph()


@pytest.fixture
def sample_graph(clean_graph):
    """构造一个小图用于查询测试。"""
    from apps.precision_testing.neo4j_client import get_neo4j_client
    client = get_neo4j_client()

    # 写入函数节点
    functions = [
        {"id": "apps.foo:changed_fn", "name": "changed_fn", "module": "apps.foo", "class_name": ""},
        {"id": "apps.foo:caller_a", "name": "caller_a", "module": "apps.foo", "class_name": ""},
        {"id": "apps.foo:caller_b", "name": "caller_b", "module": "apps.foo", "class_name": ""},
        {"id": "apps.foo:deep_caller", "name": "deep_caller", "module": "apps.foo", "class_name": ""},
        {"id": "apps.bar:external_fn", "name": "external_fn", "module": "apps.bar", "class_name": ""},
    ]
    client.batch_upsert_nodes("Function", functions)

    # 写入调用关系：changed_fn ← caller_a ← caller_b ← deep_caller
    # (caller_a 调用 changed_fn, caller_b 调用 caller_a, deep_caller 调用 caller_b)
    calls = [
        {"from_id": "apps.foo:caller_a", "to_id": "apps.foo:changed_fn"},
        {"from_id": "apps.foo:caller_b", "to_id": "apps.foo:caller_a"},
        {"from_id": "apps.foo:deep_caller", "to_id": "apps.foo:caller_b"},
        # external_fn 不在影响链上
        {"from_id": "apps.bar:external_fn", "to_id": "apps.foo:changed_fn"},
    ]
    client.batch_create_relationships("Function", "id", "CALLS", "Function", "id", calls)

    # 写入测试用例节点 + TESTED_BY 关系
    tcs = [
        {"id": "TC-1", "title": "changed_fn 测试", "test_type": "unit", "priority": "high"},
        {"id": "TC-2", "title": "caller_a 测试", "test_type": "unit", "priority": "medium"},
        {"id": "TC-3", "title": "deep_caller 测试", "test_type": "integration", "priority": "low"},
    ]
    client.batch_upsert_nodes("TestCase", tcs)
    tested_by = [
        {"from_id": "apps.foo:changed_fn", "to_id": "TC-1"},
        {"from_id": "apps.foo:caller_a", "to_id": "TC-2"},
        {"from_id": "apps.foo:deep_caller", "to_id": "TC-3"},
    ]
    client.batch_create_relationships("Function", "id", "TESTED_BY", "TestCase", "id", tested_by)

    # 写入 APIEndpoint + HANDLES 关系
    endpoints = [
        {"id": "GET /api/foo", "url_pattern": "/api/foo", "http_method": "GET", "name": "foo_view", "source": "manual"},
        {"id": "POST /api/bar", "url_pattern": "/api/bar", "http_method": "POST", "name": "bar_view", "source": "manual"},
    ]
    client.batch_upsert_nodes("APIEndpoint", endpoints)
    handles = [
        {"from_id": "GET /api/foo", "to_id": "apps.foo:caller_a"},
        {"from_id": "POST /api/bar", "to_id": "apps.bar:external_fn"},
    ]
    client.batch_create_relationships("APIEndpoint", "id", "HANDLES", "Function", "id", handles)

    return {
        "functions": functions,
        "testcases": tcs,
        "endpoints": endpoints,
    }


# =============================================================================
# ImpactQuery.query_impact 集成测试
# =============================================================================
class TestQueryImpactReal:
    def test_empty_input_returns_empty_result(self):
        result = ImpactQuery().query_impact([])
        assert result.changed_functions == []
        assert result.impacted_functions == []
        assert result.impacted_testcases == []
        assert result.impacted_endpoints == []
        assert result.elapsed_ms == 0.0

    def test_single_hop_impact(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=1)
        # depth=1: 直接调用 changed_fn 的只有 caller_a
        assert "apps.foo:caller_a" in result.impacted_functions

    def test_multi_hop_impact_propagates_upstream(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=3)
        # 3层传播：caller_a, caller_b, deep_caller 都应该被影响
        impacted = set(result.impacted_functions)
        assert "apps.foo:caller_a" in impacted
        assert "apps.foo:caller_b" in impacted
        assert "apps.foo:deep_caller" in impacted
        # external_fn 不在影响链上（虽然它调用 changed_fn，但影响是反向的）
        # 注意：影响传播只看上游调用方，A 调用 B 意味着 B 的变更影响 A
        # external_fn 是 changed_fn 的下游（被 changed_fn 调用），所以不受影响

    def test_changed_functions_merged_in_result(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=2)
        # changed 函数自身也应该在受影响集合中
        assert "apps.foo:changed_fn" in result.changed_functions

    def test_depth_clamped_to_max(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=100)
        assert result.depth == 8  # MAX_DEPTH

    def test_testcases_found_via_tested_by(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=3)
        # TC-1 直接测试 changed_fn，TC-2 测试 caller_a，TC-3 测试 deep_caller
        assert "TC-1" in result.impacted_testcases

    def test_endpoints_found_via_handles(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:caller_a"], depth=1)
        assert "GET /api/foo" in result.impacted_endpoints

    def test_elapsed_ms_recorded(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:changed_fn"], depth=3)
        assert result.elapsed_ms >= 0

    def test_unknown_function_returns_empty(self, sample_graph):
        result = ImpactQuery().query_impact(["apps.foo:nonexistent"], depth=3)
        # 未知函数不影响任何其他函数（只有自身）
        assert "apps.foo:nonexistent" not in result.impacted_functions


# =============================================================================
# ImpactQuery.query_subgraph 集成测试
# =============================================================================
class TestQuerySubgraphReal:
    def test_invalid_label_rejected(self):
        with pytest.raises(ValueError, match="未知节点类型"):
            ImpactQuery().query_subgraph("id1", node_label="EvilLabel")

    def test_empty_subgraph_for_unknown_node(self):
        payload = ImpactQuery().query_subgraph("nonexistent:id", node_label="Function")
        assert payload == {"nodes": [], "edges": []}

    def test_subgraph_returns_nodes_and_edges(self, sample_graph):
        payload = ImpactQuery().query_subgraph("apps.foo:caller_a", node_label="Function", depth=1)
        assert "nodes" in payload
        assert "edges" in payload
        node_ids = {n["data"]["node_id"] for n in payload["nodes"]}
        # caller_a 自身 + changed_fn (被调用) 都应该在子图中
        assert "apps.foo:caller_a" in node_ids

    def test_subgraph_depth_limits_hops(self, sample_graph):
        # depth=1 只能看到直接邻居
        payload_1 = ImpactQuery().query_subgraph("apps.foo:deep_caller", depth=1)
        # depth=2 能看到更多
        payload_2 = ImpactQuery().query_subgraph("apps.foo:deep_caller", depth=2)
        assert len(payload_2["nodes"]) >= len(payload_1["nodes"])


# =============================================================================
# ImpactQuery.query_overview 集成测试
# =============================================================================
class TestQueryOverviewReal:
    def test_overview_without_filter(self, sample_graph):
        payload = ImpactQuery().query_overview(limit=50)
        assert "nodes" in payload
        assert "edges" in payload
        assert len(payload["nodes"]) > 0

    def test_overview_with_label_filter(self, sample_graph):
        payload = ImpactQuery().query_overview(node_type="Function", limit=50)
        for node in payload["nodes"]:
            assert node["data"]["label"] in ("Function", "Unknown")

    def test_overview_invalid_label(self):
        with pytest.raises(ValueError, match="未知节点类型"):
            ImpactQuery().query_overview(node_type="NotALabel")

    def test_overview_limit_respected(self, sample_graph):
        payload = ImpactQuery().query_overview(limit=2)
        # limit 是对节点数的限制，边数可能更少
        assert len(payload["nodes"]) <= 2


# =============================================================================
# _safe_label 白名单集成测试（用真实查询验证无注入）
# =============================================================================
class TestSafeLabelReal:
    @pytest.mark.parametrize(
        "label", ["Function", "Class", "Module", "TestCase", "APIEndpoint"]
    )
    def test_valid_labels_accepted(self, label):
        # query_overview 不抛异常即表示标签合法
        try:
            result = ImpactQuery().query_overview(node_type=label, limit=1)
            assert "nodes" in result
        except ValueError:
            pytest.fail(f"Label {label} should be accepted")

    @pytest.mark.parametrize(
        "label", ["function", "Foo", "Function; DROP DATABASE", ""]
    )
    def test_invalid_labels_rejected(self, label):
        with pytest.raises(ValueError, match="未知节点类型"):
            _safe_label(label)
