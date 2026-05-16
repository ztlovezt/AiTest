"""Neo4jClient 单元测试。

覆盖目标:
    * 单例模式行为
    * Driver 延迟初始化与配置读取
    * verify_connectivity / close 生命周期
    * execute_read / execute_write 事务封装
    * batch_upsert_nodes / batch_create_relationships 空输入快路径
    * get_tested_by / get_impacted_functions / clear_graph / count_nodes
    * get_neo4j_client 工厂函数
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.precision_testing import neo4j_client as nc_module
from apps.precision_testing.neo4j_client import Neo4jClient, get_neo4j_client


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_singleton():
    """每个用例结束后重置 Neo4jClient 单例，避免状态泄漏。"""
    yield
    Neo4jClient._instance = None
    Neo4jClient._driver = None


@pytest.fixture
def mock_driver(monkeypatch):
    """返回 mock Driver 及其构造记录，并注入到模块。"""
    driver_mock = MagicMock()
    session_mock = MagicMock()
    tx_mock = MagicMock()

    driver_mock.session.return_value.__enter__ = lambda *a: session_mock
    driver_mock.session.return_value.__exit__ = lambda *a: None
    session_mock.begin_transaction.return_value = tx_mock
    tx_mock.run.return_value = []
    tx_mock.commit.return_value = None
    tx_mock.close.return_value = None

    fake_driver = MagicMock(side_effect=lambda *a, **kw: driver_mock)
    monkeypatch.setattr(nc_module.GraphDatabase, "driver", fake_driver)
    return driver_mock, session_mock, tx_mock, fake_driver


# ----------------------------------------------------------------------
# 单例与生命周期
# ----------------------------------------------------------------------
class TestSingletonLifecycle:
    def test_singleton_returns_same_instance(self) -> None:
        c1 = Neo4jClient()
        c2 = Neo4jClient()
        assert c1 is c2

    def test_get_neo4j_client_returns_singleton(self) -> None:
        c1 = get_neo4j_client()
        c2 = get_neo4j_client()
        assert c1 is c2
        assert isinstance(c1, Neo4jClient)

    def test_driver_lazy_initialized_on_first_access(self, mock_driver) -> None:
        driver_mock, _, _, _ = mock_driver
        client = Neo4jClient()
        assert client._driver is None
        _ = client.driver
        driver_mock.session.assert_not_called()  # driver 创建时不触发 session

    def test_driver_uses_settings_defaults(self, mock_driver, monkeypatch) -> None:
        """未配置 settings 时回退到 localhost 默认。"""
        _, _, _, fake_driver = mock_driver
        monkeypatch.delattr("django.conf.settings.NEO4J_URI", raising=False)
        monkeypatch.delattr("django.conf.settings.NEO4J_USER", raising=False)
        monkeypatch.delattr("django.conf.settings.NEO4J_PASSWORD", raising=False)
        client = Neo4jClient()
        _ = client.driver  # 触发初始化
        call_args = fake_driver.call_args
        assert call_args[0][0] == "bolt://localhost:7687"
        assert call_args[1]["auth"] == ("neo4j", "testhub")

    def test_verify_connectivity_returns_true(self, mock_driver) -> None:
        driver_mock, _, _, _ = mock_driver
        driver_mock.verify_connectivity.return_value = None
        assert Neo4jClient().verify_connectivity() is True

    def test_verify_connectivity_returns_false_on_error(self, mock_driver) -> None:
        driver_mock, _, _, _ = mock_driver
        driver_mock.verify_connectivity.side_effect = Exception("conn refused")
        assert Neo4jClient().verify_connectivity() is False

    def test_close_releases_driver(self, mock_driver) -> None:
        driver_mock, _, _, _ = mock_driver
        client = Neo4jClient()
        client._driver = driver_mock
        client.close()
        driver_mock.close.assert_called_once()
        assert client._driver is None

    def test_close_is_noop_when_no_driver(self) -> None:
        client = Neo4jClient()
        client._driver = None
        client.close()  # 不应抛异常


# ----------------------------------------------------------------------
# 底层查询封装
# ----------------------------------------------------------------------
class TestExecuteQueries:
    def test_execute_read_returns_records(self, mock_driver) -> None:
        driver_mock, session_mock, tx_mock, _ = mock_driver
        record1 = MagicMock()
        record1.data.return_value = {"a": 1}
        record2 = MagicMock()
        record2.data.return_value = {"a": 2}
        tx_mock.run.return_value = [record1, record2]

        result = Neo4jClient().execute_read("MATCH (n) RETURN n.a AS a", {"p": 1})
        assert result == [{"a": 1}, {"a": 2}]
        tx_mock.run.assert_called_once_with("MATCH (n) RETURN n.a AS a", {"p": 1})
        tx_mock.commit.assert_called_once()
        tx_mock.close.assert_called_once()

    def test_execute_write_returns_records(self, mock_driver) -> None:
        driver_mock, session_mock, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        result = Neo4jClient().execute_write("CREATE (n)", {})
        assert result == []
        tx_mock.commit.assert_called_once()

    def test_execute_read_commits_even_for_read(self, mock_driver) -> None:
        """当前实现显式 commit，确保事务关闭前提交。"""
        _, _, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        Neo4jClient().execute_read("MATCH (n) RETURN n")
        tx_mock.commit.assert_called_once()
        tx_mock.close.assert_called_once()


# ----------------------------------------------------------------------
# 批量写入
# ----------------------------------------------------------------------
class TestBatchOperations:
    def test_batch_upsert_nodes_empty_is_noop(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        Neo4jClient().batch_upsert_nodes("Function", [])
        tx_mock.run.assert_not_called()

    def test_batch_upsert_nodes_generates_unwind_merge(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        nodes = [{"id": "fn1", "name": "foo"}, {"id": "fn2", "name": "bar"}]
        Neo4jClient().batch_upsert_nodes("Function", nodes, key="id")
        query, params = tx_mock.run.call_args[0]
        assert "UNWIND $nodes AS node" in query
        assert "MERGE (n:Function {id: node.id})" in query
        assert "SET n += node" in query
        assert params["nodes"] == nodes

    def test_batch_create_rels_empty_is_noop(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        Neo4jClient().batch_create_relationships(
            "Function", "id", "CALLS", "Function", "id", []
        )
        tx_mock.run.assert_not_called()

    def test_batch_create_rels_generates_unwind_match_merge(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        rels = [{"from_id": "a", "to_id": "b", "properties": {"line": 1}}]
        Neo4jClient().batch_create_relationships(
            "Function", "id", "CALLS", "Function", "id", rels
        )
        query, params = tx_mock.run.call_args[0]
        assert "UNWIND $rels AS rel" in query
        assert "MATCH (a:Function {id: rel.from_id})" in query
        assert "(b:Function {id: rel.to_id})" in query
        assert "MERGE (a)-[r:CALLS]->(b)" in query
        assert params["rels"] == rels


# ----------------------------------------------------------------------
# 图查询辅助
# ----------------------------------------------------------------------
class TestGraphQueries:
    def test_get_tested_by_empty_returns_empty(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        assert Neo4jClient().get_tested_by([]) == []
        tx_mock.run.assert_not_called()

    def test_get_tested_by_returns_distinct_ids(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        record1 = MagicMock()
        record1.data.return_value = {"testcase_id": "TC-1"}
        record2 = MagicMock()
        record2.data.return_value = {"testcase_id": "TC-2"}
        tx_mock.run.return_value = [record1, record2]
        result = Neo4jClient().get_tested_by(["fn1", "fn2"])
        assert result == ["TC-1", "TC-2"]
        query, params = tx_mock.run.call_args[0]
        assert "TESTED_BY" in query
        assert params["function_ids"] == ["fn1", "fn2"]

    def test_get_impacted_functions_empty_returns_empty(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        assert Neo4jClient().get_impacted_functions([]) == []
        tx_mock.run.assert_not_called()

    def test_get_impacted_functions_filters_none(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        r1 = MagicMock()
        r1.data.return_value = {"function_id": "fn1"}
        r2 = MagicMock()
        r2.data.return_value = {"function_id": None}
        r3 = MagicMock()
        r3.data.return_value = {"function_id": "fn2"}
        tx_mock.run.return_value = [r1, r2, r3]
        result = Neo4jClient().get_impacted_functions(["changed"])
        assert result == ["fn1", "fn2"]
        query, _ = tx_mock.run.call_args[0]
        assert "CALLS*1..5" in query

    def test_clear_graph_executes_detach_delete(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        tx_mock.run.return_value = []
        Neo4jClient().clear_graph()
        query, _ = tx_mock.run.call_args[0]
        assert "MATCH (n) DETACH DELETE n" in query

    def test_count_nodes_returns_label_mapping(self, mock_driver) -> None:
        _, _, tx_mock, _ = mock_driver
        r1 = MagicMock()
        r1.data.return_value = {"label": "Function", "cnt": 100}
        r2 = MagicMock()
        r2.data.return_value = {"label": "Class", "cnt": 20}
        tx_mock.run.return_value = [r1, r2]
        result = Neo4jClient().count_nodes()
        assert result == {"Function": 100, "Class": 20}

    def test_count_nodes_handles_none_label(self, mock_driver) -> None:
        """count_nodes 直接透传 label 值，None 也会保留（与 verify_graph 不同）。"""
        _, _, tx_mock, _ = mock_driver
        r1 = MagicMock()
        r1.data.return_value = {"label": None, "cnt": 5}
        tx_mock.run.return_value = [r1]
        result = Neo4jClient().count_nodes()
        assert result == {None: 5}
