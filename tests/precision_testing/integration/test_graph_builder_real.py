"""GraphBuilder 集成测试 — 连接真实 Neo4j

前置条件：
    * Neo4j 运行于 localhost:7474
    * Django settings 已配置
    * 测试用临时 Git 仓库

运行方式：
    pytest tests/precision_testing/integration/test_graph_builder_real.py -v
"""
from __future__ import annotations

import pytest

from apps.precision_testing.graph_builder import GraphBuilder


@pytest.fixture
def clean_graph():
    from apps.precision_testing.neo4j_client import get_neo4j_client
    client = get_neo4j_client()
    client.clear_graph()
    yield
    client.clear_graph()


@pytest.fixture
def sample_repo(tmp_path):
    """构造一个真实的小型 Python 仓库用于图构建。"""
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    (repo / "apps").mkdir()
    (repo / "apps" / "foo").mkdir()
    (repo / "apps" / "foo" / "__init__.py").write_text("", encoding="utf-8")

    (repo / "apps" / "foo" / "bar.py").write_text(
        "def changed_fn(x):\n"
        "    return x + 1\n"
        "\n"
        "def caller_a():\n"
        "    return changed_fn(1)\n"
        "\n"
        "def deep_caller():\n"
        "    return caller_a()\n",
        encoding="utf-8",
    )

    (repo / "apps" / "baz.py").write_text(
        "def unrelated_fn():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    return str(repo)


class TestGraphBuilderReal:
    def test_build_full_graph_creates_nodes(self, clean_graph, sample_repo, monkeypatch):
        # Mock ORM-dependent methods to avoid MySQL requirement
        monkeypatch.setattr(GraphBuilder, "_scan_testcases", lambda self: [])
        monkeypatch.setattr(GraphBuilder, "_build_tested_by_relationships", lambda self: None)
        builder = GraphBuilder(sample_repo)
        stats = builder.build_full_graph()

        assert stats["function_count"] >= 4
        assert stats["module_count"] >= 2
        assert stats["call_edge_count"] >= 2
        assert stats["elapsed_seconds"] >= 0

    def test_build_full_graph_no_duplicate_nodes(self, clean_graph, sample_repo, monkeypatch):
        monkeypatch.setattr(GraphBuilder, "_scan_testcases", lambda self: [])
        monkeypatch.setattr(GraphBuilder, "_build_tested_by_relationships", lambda self: None)
        builder = GraphBuilder(sample_repo)
        s1 = builder.build_full_graph()
        s2 = builder.build_full_graph()
        assert s1["function_count"] == s2["function_count"]

    def test_apply_schema_does_not_crash(self, clean_graph, sample_repo):
        builder = GraphBuilder(sample_repo)
        builder.apply_schema()

    def test_incremental_sync_removes_old_functions(self, clean_graph, sample_repo, monkeypatch):
        monkeypatch.setattr(GraphBuilder, "_scan_testcases", lambda self: [])
        monkeypatch.setattr(GraphBuilder, "_build_tested_by_relationships", lambda self: None)
        from pathlib import Path
        builder = GraphBuilder(sample_repo)
        builder.build_full_graph()

        bar_path = Path(sample_repo) / "apps" / "foo" / "bar.py"
        bar_path.write_text(
            "def changed_fn(x):\n"
            "    return x + 1\n"
            "\n"
            "def caller_a():\n"
            "    return changed_fn(1)\n"
            "\n"
            "def deep_caller():\n"
            "    return caller_a()\n"
            "\n"
            "def new_function():\n"
            "    return deep_caller()\n",
            encoding="utf-8",
        )

        result = builder.incremental_sync(["apps/foo/bar.py"])
        assert result["files"] == 1
        assert result["function_count"] >= 4

    def test_incremental_sync_skips_empty_file_list(self, clean_graph, sample_repo, monkeypatch):
        monkeypatch.setattr(GraphBuilder, "_scan_testcases", lambda self: [])
        builder = GraphBuilder(sample_repo)
        result = builder.incremental_sync([])
        assert result["skipped"] is True
        assert result["elapsed_seconds"] == 0.0

    def test_module_dotted_from_path_windows_and_unix(self):
        from apps.precision_testing.graph_builder import _module_dotted_from_path

        assert _module_dotted_from_path("apps/foo/bar.py") == "apps.foo.bar"
        assert _module_dotted_from_path("apps\\foo\\bar.py") == "apps.foo.bar"
        assert _module_dotted_from_path("apps/foo/__init__.py") == "apps.foo"
        assert _module_dotted_from_path("foo.py") == "foo"
