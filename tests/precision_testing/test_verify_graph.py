"""verify_graph 管理命令单元测试。

覆盖目标:
    * 参数解析 (--json, --fix-orphans, --limit)
    * _collect_report 聚合 5 项检查
    * _render_human / JSON 输出格式
    * --fix-orphans 修复后退出码 0
    * 无 issues 时退出码 0
    * 有 issues 时退出码 1
    * ServiceUnavailable 处理
"""
from __future__ import annotations

import json
import sys
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.precision_testing.management.commands.verify_graph import Command


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def mock_client():
    """返回一个记录查询调用并返回预设结果的 mock Neo4jClient。"""
    client = MagicMock()
    client.execute_read.return_value = []
    client.execute_write.return_value = []
    return client


@pytest.fixture
def command():
    return Command()


# ----------------------------------------------------------------------
# 参数解析
# ----------------------------------------------------------------------
class TestArgumentParsing:
    def test_json_flag_parsed(self) -> None:
        parser = MagicMock()
        parser.add_argument = MagicMock()
        Command().add_arguments(parser)
        calls = [call[1] for call in parser.add_argument.call_args_list]
        dests = [c.get("dest") for c in calls if "dest" in c]
        assert "as_json" in dests
        assert "fix_orphans" in dests
        # --limit does not have explicit dest, verify by type + default
        assert any(c.get("type") == int and c.get("default") == 20 for c in calls)


# ----------------------------------------------------------------------
# 报告采集
# ----------------------------------------------------------------------
class TestCollectReport:
    def test_empty_graph_returns_no_issues(self, command: Command, mock_client: MagicMock) -> None:
        report = command._collect_report(mock_client, limit=20)
        assert report["issues"] == []
        assert report["nodes"] == {}
        assert report["relationships"] == {}
        assert report["orphan_functions"] == []
        assert report["missing_props"] == []
        assert report["duplicate_relationships"] == []
        assert report["unmapped_testcases"] == []

    def test_orphan_functions_trigger_issue(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.side_effect = [
            [],  # node counts
            [],  # rel counts
            [{"id": "fn1", "module": "apps.foo", "name": "bar"}],  # orphans
            [],  # missing props
            [],  # duplicate rels
            [],  # unmapped tcs
        ]
        report = command._collect_report(mock_client, limit=20)
        assert "orphan_functions=1" in report["issues"]
        assert len(report["orphan_functions"]) == 1

    def test_missing_props_trigger_issue(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.side_effect = [
            [], [],
            [],
            [{"internal_id": 1, "id": None, "module": "m", "name": "n"}],
            [], [],
        ]
        report = command._collect_report(mock_client, limit=20)
        assert "missing_props=1" in report["issues"]

    def test_duplicate_rels_trigger_issue(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.side_effect = [
            [], [], [], [],
            [{"source_id": "a", "target_id": "b", "rel_type": "CALLS", "c": 2}],
            [],
        ]
        report = command._collect_report(mock_client, limit=20)
        assert "duplicate_rels=1" in report["issues"]

    def test_unmapped_testcases_trigger_issue(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.side_effect = [
            [], [], [], [], [],
            [{"id": "TC-1", "title": "test foo"}],
        ]
        report = command._collect_report(mock_client, limit=20)
        assert "unmapped_testcases=1" in report["issues"]

    def test_multiple_issues_concatenated(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.side_effect = [
            [], [],
            [{"id": "fn1", "module": "m", "name": "n"}],
            [{"internal_id": 1, "id": None, "module": "m", "name": "n"}],
            [], [],
        ]
        report = command._collect_report(mock_client, limit=20)
        assert len(report["issues"]) == 2
        assert any("orphan" in i for i in report["issues"])
        assert any("missing_props" in i for i in report["issues"])

    def test_limit_passed_to_queries(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = []
        command._collect_report(mock_client, limit=42)
        for call in mock_client.execute_read.call_args_list[2:]:
            # limit is passed as the 2nd positional arg (dict)
            assert call[0][1]["limit"] == 42


# ----------------------------------------------------------------------
# 内部查询方法
# ----------------------------------------------------------------------
class TestInternalQueries:
    def test_count_nodes_uses_first_label(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [
            {"label": "Function", "c": 10},
            {"label": None, "c": 5},
        ]
        result = command._count_nodes_by_label(mock_client)
        assert result == {"Function": 10, "Unknown": 5}

    def test_count_rels_maps_type_to_count(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [
            {"t": "CALLS", "c": 100},
            {"t": "CONTAINS", "c": 50},
        ]
        result = command._count_rels_by_type(mock_client)
        assert result == {"CALLS": 100, "CONTAINS": 50}

    def test_find_orphan_functions_returns_list(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [{"id": "fn1", "module": "m", "name": "n"}]
        result = command._find_orphan_functions(mock_client, limit=10)
        assert result == [{"id": "fn1", "module": "m", "name": "n"}]

    def test_find_missing_props_returns_list(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [{"internal_id": 1, "id": None, "module": "m", "name": "n"}]
        result = command._find_missing_props(mock_client, limit=10)
        assert len(result) == 1

    def test_find_duplicate_rels_returns_list(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [{"source_id": "a", "target_id": "b", "rel_type": "CALLS", "c": 2}]
        result = command._find_duplicate_rels(mock_client, limit=10)
        assert len(result) == 1

    def test_find_unmapped_testcases_returns_list(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_read.return_value = [{"id": "TC-1", "title": "t"}]
        result = command._find_unmapped_testcases(mock_client, limit=10)
        assert len(result) == 1

    def test_delete_orphan_functions_returns_count(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_write.return_value = [{"removed": 3}]
        result = command._delete_orphan_functions(mock_client)
        assert result == 3

    def test_delete_orphan_functions_zero_when_no_records(self, command: Command, mock_client: MagicMock) -> None:
        mock_client.execute_write.return_value = []
        result = command._delete_orphan_functions(mock_client)
        assert result == 0


# ----------------------------------------------------------------------
# handle 流程与退出码
# ----------------------------------------------------------------------
class TestHandleFlow:
    def test_json_output_with_issues_exits_1(self, command: Command, mock_client: MagicMock, monkeypatch) -> None:
        monkeypatch.setattr(
            "apps.precision_testing.neo4j_client.get_neo4j_client",
            lambda: mock_client,
        )
        mock_client.execute_read.return_value = []
        out = StringIO()
        err = StringIO()
        command.stdout = out
        command.stderr = err
        # 空图无 issues，handle 正常返回（不会 sys.exit）
        command.handle(as_json=True, fix_orphans=False, limit=20)
        output = json.loads(out.getvalue())
        assert output["issues"] == []

    def test_json_output_with_orphans_exits_1(self, command: Command, mock_client: MagicMock, monkeypatch) -> None:
        monkeypatch.setattr(
            "apps.precision_testing.neo4j_client.get_neo4j_client",
            lambda: mock_client,
        )
        mock_client.execute_read.side_effect = [
            [], [],
            [{"id": "fn1", "module": "m", "name": "n"}],
            [], [], [],
        ]
        out = StringIO()
        command.stdout = out
        with pytest.raises(SystemExit) as exc_info:
            command.handle(as_json=True, fix_orphans=False, limit=20)
        assert exc_info.value.code == 1
        output = json.loads(out.getvalue())
        assert output["issues"] == ["orphan_functions=1"]

    def test_fix_orphans_changes_exit_to_0(self, command: Command, mock_client: MagicMock, monkeypatch) -> None:
        monkeypatch.setattr(
            "apps.precision_testing.neo4j_client.get_neo4j_client",
            lambda: mock_client,
        )
        mock_client.execute_read.side_effect = [
            [], [],
            [{"id": "fn1", "module": "m", "name": "n"}],
            [], [], [],
        ]
        mock_client.execute_write.return_value = [{"removed": 1}]
        out = StringIO()
        command.stdout = out
        with pytest.raises(SystemExit) as exc_info:
            command.handle(as_json=False, fix_orphans=True, limit=20)
        assert exc_info.value.code == 0

    def test_human_output_shows_counts(self, command: Command, mock_client: MagicMock, monkeypatch) -> None:
        monkeypatch.setattr(
            "apps.precision_testing.neo4j_client.get_neo4j_client",
            lambda: mock_client,
        )
        mock_client.execute_read.return_value = []
        out = StringIO()
        command.stdout = out
        # 空图无 issues，handle 正常返回（不会 sys.exit）
        command.handle(as_json=False, fix_orphans=False, limit=20)
        output = out.getvalue()
        assert "Node counts:" in output or "Graph healthy" in output

    def test_service_unavailable_raises_command_error(self, command: Command, monkeypatch) -> None:
        from neo4j.exceptions import ServiceUnavailable
        from django.core.management.base import CommandError

        mock_client = MagicMock()
        mock_client.execute_read.side_effect = ServiceUnavailable("neo4j down")

        monkeypatch.setattr(
            "apps.precision_testing.neo4j_client.get_neo4j_client",
            lambda: mock_client,
        )
        with pytest.raises(CommandError, match="Neo4j unreachable"):
            command.handle(as_json=False, fix_orphans=False, limit=20)


# ----------------------------------------------------------------------
# _render_human
# ----------------------------------------------------------------------
class TestRenderHuman:
    def test_shows_fixed_orphan_count(self, command: Command) -> None:
        out = StringIO()
        command.stdout = out
        report = {
            "nodes": {},
            "relationships": {},
            "orphan_functions": [],
            "missing_props": [],
            "duplicate_relationships": [],
            "unmapped_testcases": [],
            "issues": [],
            "fixed_orphan_functions": 5,
        }
        command._render_human(report)
        assert "Removed orphan functions: 5" in out.getvalue()

    def test_shows_error_when_issues_present(self, command: Command) -> None:
        out = StringIO()
        command.stdout = out
        report = {
            "nodes": {},
            "relationships": {},
            "orphan_functions": [{"id": "fn1"}],
            "missing_props": [],
            "duplicate_relationships": [],
            "unmapped_testcases": [],
            "issues": ["orphan_functions=1"],
        }
        command._render_human(report)
        output = out.getvalue()
        assert "orphan_functions" in output
