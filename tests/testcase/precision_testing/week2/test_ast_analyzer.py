# -*- coding: utf-8 -*-
"""Week2: Git Diff + AST 解析引擎 — ASTAnalyzer 公共 API 测试用例

覆盖模块: backend/apps/precision_testing/ast_analyzer.py
目标覆盖率: 80%+
生成时间: 2026-05-08
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保 apps.precision_testing 可导入
# week2: tests/testcase/precision_testing/week2/test_foo.py → parents[4] = testhub_platform/
_test_file = Path(__file__).resolve()
sys.path.insert(0, str(_test_file.parents[4] / "backend"))

try:
    from apps.precision_testing.ast_analyzer import (
        ASTAnalyzer,
        FunctionRecord,
        CallEdge,
        normalize_module_path,
        _extract_decorator_names,
        _decorator_name,
    )
except ImportError:
    pytest.skip("apps.precision_testing.ast_analyzer not available", allow_module_level=True)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def temp_repo_path(tmp_path: Path) -> Path:
    """模拟仓库根路径。"""
    apps_dir = tmp_path / "apps" / "projects"
    apps_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def analyzer(temp_repo_path: Path) -> ASTAnalyzer:
    return ASTAnalyzer(repo_path=str(temp_repo_path))


# ==============================================================================
# 数据类测试 — FunctionRecord
# ==============================================================================

class TestFunctionRecord:
    """FunctionRecord 数据类测试。"""

    def test_to_dict_all_fields(self) -> None:
        rec = FunctionRecord(
            file="apps/projects/views.py",
            module="apps.projects.views",
            signature="apps.projects.views:ProjectViewSet.list",
            name="list",
            qualified_name="ProjectViewSet.list",
            class_name="ProjectViewSet",
            is_async=False,
            is_action=True,
            decorators=("action", "csrf_exempt"),
            start_line=10,
            end_line=25,
            body_start_line=15,
            lineno_def=15,
        )
        d = rec.to_dict()
        assert d["file"] == "apps/projects/views.py"
        assert d["signature"] == "apps.projects.views:ProjectViewSet.list"
        assert d["is_async"] is False
        assert d["is_action"] is True
        assert d["decorators"] == ["action", "csrf_exempt"]
        assert d["start_line"] == 10
        assert d["end_line"] == 25
        assert d["body_start_line"] == 15

    def test_covers(self) -> None:
        rec = FunctionRecord(
            file="x.py", module="x", signature="x:f",
            name="f", qualified_name="f", class_name="",
            is_async=False, is_action=False, decorators=(),
            start_line=10, end_line=20, body_start_line=12, lineno_def=12,
        )
        assert rec.covers(10) is True
        assert rec.covers(15) is True
        assert rec.covers(20) is True
        assert rec.covers(9) is False
        assert rec.covers(21) is False

    def test_immutable(self) -> None:
        rec = FunctionRecord(
            file="x.py", module="x", signature="x:f",
            name="f", qualified_name="f", class_name="",
            is_async=False, is_action=False, decorators=(),
            start_line=1, end_line=10, body_start_line=1, lineno_def=1,
        )
        with pytest.raises(Exception):
            rec.start_line = 99  # type: ignore


# ==============================================================================
# 数据类测试 — CallEdge
# ==============================================================================

class TestCallEdge:
    """CallEdge 数据类测试。"""

    def test_to_dict(self) -> None:
        edge = CallEdge(
            caller_signature="a:b",
            callee_name="foo",
            callee_module="c.d",
            line=42,
        )
        d = edge.to_dict()
        assert d["caller_signature"] == "a:b"
        assert d["callee_name"] == "foo"
        assert d["callee_module"] == "c.d"
        assert d["line"] == 42

    def test_callee_module_can_be_none(self) -> None:
        edge = CallEdge(caller_signature="a:b", callee_name="foo", callee_module=None, line=1)
        assert edge.callee_module is None


# ==============================================================================
# normalize_module_path
# ==============================================================================

class TestNormalizeModulePath:
    """normalize_module_path 辅助函数测试。"""

    def test_apps_path_to_dotted(self) -> None:
        assert normalize_module_path("apps/projects/views.py") == "apps.projects.views"
        assert normalize_module_path("apps/foo/__init__.py") == "apps.foo"

    def test_slashes_to_dots(self) -> None:
        assert normalize_module_path("a/b/c.py") == "a.b.c"

    def test_backslash_to_slash(self) -> None:
        assert normalize_module_path("a\\b\\c.py") == "a.b.c"

    def test_strips_init(self) -> None:
        assert normalize_module_path("apps/__init__.py") == "apps"
        assert normalize_module_path("apps/views/__init__.py") == "apps.views"

    def test_no_py_extension(self) -> None:
        assert normalize_module_path("apps/foo/bar") == "apps.foo.bar"

    def test_leading_dot_slash(self) -> None:
        assert normalize_module_path("./apps/views.py") == "apps.views"


# ==============================================================================
# ASTAnalyzer — 初始化
# ==============================================================================

class TestASTAnalyzerInit:
    """ASTAnalyzer 构造测试。"""

    def test_repo_path_resolved(self, temp_repo_path: Path) -> None:
        analyzer = ASTAnalyzer(repo_path=str(temp_repo_path))
        assert analyzer.repo_path == temp_repo_path.resolve()

    def test_repo_path_nonexistent_no_error(self, tmp_path: Path) -> None:
        """ASTAnalyzer 不验证路径是否存在(延迟到解析时)。"""
        analyzer = ASTAnalyzer(repo_path=str(tmp_path / "nonexistent"))
        assert analyzer.repo_path == (tmp_path / "nonexistent").resolve()


# ==============================================================================
# ASTAnalyzer — parse_source
# ==============================================================================

class TestParseSource:
    """parse_source 方法测试。"""

    def test_parses_function(self, analyzer: ASTAnalyzer) -> None:
        source = "def foo():\n    pass\n"
        records = analyzer.parse_source(source, "test.py")
        assert len(records) == 1
        assert records[0].name == "foo"
        assert records[0].signature == "test:foo"
        assert records[0].class_name == ""

    def test_parses_async_function(self, analyzer: ASTAnalyzer) -> None:
        source = "async def bar():\n    await something()\n"
        records = analyzer.parse_source(source, "test.py")
        assert len(records) == 1
        assert records[0].is_async is True
        assert records[0].name == "bar"

    def test_parses_class_method(self, analyzer: ASTAnalyzer) -> None:
        source = """
class MyView:
    def get(self):
        pass
"""
        records = analyzer.parse_source(source, "test.py")
        method = next((r for r in records if r.name == "get"), None)
        assert method is not None
        assert method.class_name == "MyView"
        assert method.qualified_name == "MyView.get"

    def test_nested_class_context(self, analyzer: ASTAnalyzer) -> None:
        source = """
class Outer:
    class Inner:
        def inner_method(self):
            pass
"""
        records = analyzer.parse_source(source, "test.py")
        inner_method = next((r for r in records if r.name == "inner_method"), None)
        assert inner_method is not None
        assert inner_method.class_name == "Outer.Inner"

    def test_decorator_line_is_start(self, analyzer: ASTAnalyzer) -> None:
        source = """
@login_required
@cache_page(60)
def protected_view(request):
    pass
"""
        records = analyzer.parse_source(source, "test.py")
        assert len(records) == 1
        assert records[0].start_line == 2  # @login_required
        assert records[0].decorators == ("login_required", "cache_page")

    def test_function_without_decorator(self, analyzer: ASTAnalyzer) -> None:
        source = """
def plain_func():
    pass
"""
        records = analyzer.parse_source(source, "test.py")
        assert len(records) == 1
        assert records[0].start_line == 2
        assert records[0].decorators == ()

    def test_action_decorator_detection(self, analyzer: ASTAnalyzer) -> None:
        source = """
from rest_framework.decorators import action
class FooViewSet(ViewSet):
    @action(detail=True, methods=['post'])
    def custom_action(self):
        pass

    def list(self):
        pass
"""
        records = analyzer.parse_source(source, "test.py")
        custom = next((r for r in records if r.name == "custom_action"), None)
        assert custom is not None
        assert custom.is_action is True
        assert "action" in custom.decorators

    def test_syntax_error_returns_empty(self, analyzer: ASTAnalyzer) -> None:
        source = "def foo(\n    pass  # syntax error"
        records = analyzer.parse_source(source, "bad.py")
        assert records == []

    def test_multiple_functions(self, analyzer: ASTAnalyzer) -> None:
        source = """
def f1():
    pass

def f2():
    pass

def f3():
    pass
"""
        records = analyzer.parse_source(source, "test.py")
        assert len(records) == 3
        names = {r.name for r in records}
        assert names == {"f1", "f2", "f3"}


# ==============================================================================
# ASTAnalyzer — parse_file
# ==============================================================================

class TestParseFile:
    """parse_file 方法测试。"""

    def test_parses_existing_file(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "test_file.py"
        test_file.write_text("def hello():\n    pass\n", encoding="utf-8")
        records = analyzer.parse_file("apps/test_file.py")
        assert len(records) == 1
        assert records[0].name == "hello"

    def test_file_not_found_returns_empty(self, analyzer: ASTAnalyzer) -> None:
        records = analyzer.parse_file("nonexistent/file_xyz.py")
        assert records == []

    def test_file_read_error_returns_empty(self, analyzer: ASTAnalyzer, tmp_path: Path) -> None:
        # Create a file that raises error on read
        with patch("pathlib.Path.read_text", side_effect=OSError("read error")):
            records = analyzer.parse_file("some_file.py")
            assert records == []


# ==============================================================================
# ASTAnalyzer — get_changed_function_records
# ==============================================================================

class TestGetChangedFunctionRecords:
    """get_changed_function_records 方法测试。"""

    def test_filters_to_python_files(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        diff_result = {
            "changed_files": [
                {"path": "apps/foo.py", "added_lines": [1, 2], "removed_lines": []},
                {"path": "apps/bar.txt", "added_lines": [1], "removed_lines": []},
            ]
        }
        results = analyzer.get_changed_function_records(diff_result)
        assert all(r.file.endswith(".py") for r in results)

    def test_nonexistent_file_skipped(self, analyzer: ASTAnalyzer) -> None:
        diff_result = {
            "changed_files": [
                {"path": "nonexistent/file_xyz.py", "added_lines": [1, 2], "removed_lines": []},
            ]
        }
        results = analyzer.get_changed_function_records(diff_result)
        assert results == []

    def test_empty_changed_lines_skipped(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "empty.py"
        test_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        diff_result = {
            "changed_files": [
                {"path": "apps/empty.py", "added_lines": [], "removed_lines": []},
            ]
        }
        results = analyzer.get_changed_function_records(diff_result)
        assert results == []

    def test_covers_line(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "cov.py"
        test_file.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n", encoding="utf-8")

        diff_result = {
            "changed_files": [
                {"path": "apps/cov.py", "added_lines": [2], "removed_lines": []},
            ]
        }
        results = analyzer.get_changed_function_records(diff_result)
        assert len(results) == 1
        assert results[0].name == "foo"

    def test_duplicate_signatures_deduplicated(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "dup.py"
        test_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        diff_result = {
            "changed_files": [
                {"path": "apps/dup.py", "added_lines": [1, 2], "removed_lines": [1, 2]},
            ]
        }
        results = analyzer.get_changed_function_records(diff_result)
        names = [r.name for r in results]
        assert names.count("foo") == 1

    def test_get_changed_functions_returns_dicts(self, analyzer: ASTAnalyzer) -> None:
        diff_result = {"changed_files": []}
        results = analyzer.get_changed_functions(diff_result)
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)


# ==============================================================================
# ASTAnalyzer — map_lines_to_functions
# ==============================================================================

class TestMapLinesToFunctions:
    """map_lines_to_functions 方法测试。"""

    def test_maps_line_to_function(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "m2f.py"
        test_file.write_text(
            "def foo():\n    pass\n\ndef bar():\n    pass\n",
            encoding="utf-8",
        )
        mapping = analyzer.map_lines_to_functions("apps/m2f.py", [2])
        assert 2 in mapping

    def test_line_not_in_any_function(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "empty_file.py"
        test_file.write_text("# no functions here\n", encoding="utf-8")
        mapping = analyzer.map_lines_to_functions("apps/empty_file.py", [1])
        assert mapping == {}


# ==============================================================================
# ASTAnalyzer — extract_call_edges
# ==============================================================================

class TestExtractCallEdges:
    """extract_call_edges 方法测试。"""

    def test_extracts_call_edges(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "calls.py"
        test_file.write_text(
            "def caller():\n    foo()\n    bar.baz()\n",
            encoding="utf-8",
        )
        edges = analyzer.extract_call_edges("apps/calls.py")
        assert len(edges) >= 1
        assert any(e.caller_signature == "apps.calls:caller" for e in edges)

    def test_file_not_found_returns_empty(self, analyzer: ASTAnalyzer) -> None:
        edges = analyzer.extract_call_edges("nonexistent/file_xyz.py")
        assert edges == []

    def test_astroid_available(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        """astroid 可用时能解析跨模块调用。"""
        try:
            import astroid  # noqa: F401
        except ImportError:
            pytest.skip("astroid not installed")

        test_file = temp_repo_path / "apps" / "with_import.py"
        test_file.write_text(
            "from datetime import datetime\ndef f():\n    datetime.now()\n",
            encoding="utf-8",
        )
        edges = analyzer.extract_call_edges("apps/with_import.py")
        assert isinstance(edges, list)

    def test_stdlib_fallback_when_astroid_missing(
        self, analyzer: ASTAnalyzer, temp_repo_path: Path
    ) -> None:
        """astroid 不可用时降级到 stdlib ast。"""
        test_file = temp_repo_path / "apps" / "stdlib_fallback.py"
        test_file.write_text("def f():\n    print('hi')\n", encoding="utf-8")

        with patch("apps.precision_testing.ast_analyzer.astroid", None):
            edges = analyzer.extract_call_edges("apps/stdlib_fallback.py")
            assert isinstance(edges, list)


# ==============================================================================
# ASTAnalyzer — function_for_line
# ==============================================================================

class TestFunctionForLine:
    """function_for_line 方法测试。"""

    def test_finds_function(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "ffl.py"
        test_file.write_text("def foo():\n    pass\n", encoding="utf-8")
        rec = analyzer.function_for_line("apps/ffl.py", 1)
        assert rec is not None
        assert rec.name == "foo"

    def test_line_not_in_function(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "blank.py"
        test_file.write_text("# no function\n", encoding="utf-8")
        rec = analyzer.function_for_line("apps/blank.py", 1)
        assert rec is None


# ==============================================================================
# _extract_decorator_names / _decorator_name
# ==============================================================================

class TestDecoratorHelpers:
    """装饰器相关辅助函数测试。"""

    def test_extract_decorator_names_simple(self) -> None:
        import ast
        source = "@foo\n@bar\ndef f(): pass"
        tree = ast.parse(source)
        func_def = tree.body[0]
        names = _extract_decorator_names(func_def.decorator_list)
        assert "foo" in names
        assert "bar" in names

    def test_decorator_name_attribute(self) -> None:
        import ast
        source = "@rest_framework.decorators.action\ndef f(): pass"
        tree = ast.parse(source)
        func_def = tree.body[0]
        name = _decorator_name(func_def.decorator_list[0])
        assert "action" in name

    def test_decorator_name_call(self) -> None:
        import ast
        source = "@cache_page(60)\ndef f(): pass"
        tree = ast.parse(source)
        func_def = tree.body[0]
        name = _decorator_name(func_def.decorator_list[0])
        assert name == "cache_page"


# ==============================================================================
# 场景测试 — 完整解析流程
# ==============================================================================

class TestASTAnalyzerFullWorkflow:
    """端到端场景测试。"""

    def test_django_viewset_full_parse(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        """模拟 Django ViewSet 的完整解析场景。"""
        test_file = temp_repo_path / "apps" / "views.py"
        test_file.write_text("""
from rest_framework.decorators import action
from rest_framework.views import APIView

class ProjectViewSet(APIView):
    def list(self, request):
        pass

    def retrieve(self, request, pk=None):
        pass

    @action(detail=True, methods=['post'])
    def custom_sync(self, request, pk=None):
        pass

    @action(detail=False, methods=['get'])
    def stats(self, request):
        pass
""", encoding="utf-8")

        records = analyzer.parse_file("apps/views.py")
        assert len(records) >= 4

        # Check action detection
        custom = next((r for r in records if r.name == "custom_sync"), None)
        assert custom is not None
        assert custom.is_action is True
        assert "action" in custom.decorators

        stats = next((r for r in records if r.name == "stats"), None)
        assert stats is not None
        assert stats.is_action is True

        # Check regular methods
        list_rec = next((r for r in records if r.name == "list"), None)
        assert list_rec is not None
        assert list_rec.class_name == "ProjectViewSet"

    def test_diff_result_to_changed_functions(self, analyzer: ASTAnalyzer, temp_repo_path: Path) -> None:
        """模拟 GitDiffAnalyzer 输出 → ASTAnalyzer 输入的完整链路。"""
        # Create a modified Python file
        test_file = temp_repo_path / "apps" / "changed.py"
        test_file.write_text("""
def added_func():
    pass

def another_added():
    pass
""", encoding="utf-8")

        diff_result = {
            "changed_files": [
                {
                    "path": "apps/changed.py",
                    "added_lines": [2, 3, 5, 6],
                    "removed_lines": [],
                }
            ]
        }

        changed_funcs = analyzer.get_changed_function_records(diff_result)
        assert len(changed_funcs) == 2
        names = {r.name for r in changed_funcs}
        assert "added_func" in names
        assert "another_added" in names

    def test_nested_functions(self, analyzer: ASTAnalyzer) -> None:
        """嵌套函数应各自成为独立记录。"""
        source = """
def outer():
    def inner():
        pass
    return inner
"""
        records = analyzer.parse_source(source, "nested.py")
        assert len(records) == 2
        names = {r.name for r in records}
        assert "outer" in names
        assert "inner" in names

    def test_lambda_ignored(self, analyzer: ASTAnalyzer) -> None:
        """lambda 不应被误识别为 FunctionDef。"""
        source = """
def f():
    g = lambda x: x + 1
    return g
"""
        records = analyzer.parse_source(source, "lambda_test.py")
        assert len(records) == 1
        assert records[0].name == "f"