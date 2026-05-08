"""ASTAnalyzer 单元测试。

覆盖目标:
    * 装饰器对 ``start_line`` 的影响 (``@property`` / ``@action``)
    * AsyncFunctionDef 识别
    * 嵌套类 / 嵌套函数的 qualified_name
    * @action 装饰器 → ``is_action=True``
    * ``map_lines_to_functions`` 行号 → 函数签名
    * ``get_changed_function_records`` 与 diff 结果对接
    * 旧版 ``_extract_functions`` 兼容 API
    * ``normalize_module_path`` 的边界情况
"""
from __future__ import annotations

import textwrap

import pytest

from apps.precision_testing.ast_analyzer import (
    ASTAnalyzer,
    FunctionRecord,
    normalize_module_path,
)


# ----------------------------------------------------------------------
# 模块级辅助
# ----------------------------------------------------------------------
class TestNormalizeModulePath:
    @pytest.mark.parametrize("raw,expected", [
        ("apps/projects/views.py", "apps.projects.views"),
        ("apps\\projects\\views.py", "apps.projects.views"),
        ("apps/projects/__init__.py", "apps.projects"),
        ("./apps/foo.py", "apps.foo"),
        ("foo.py", "foo"),
    ])
    def test_normalize(self, raw: str, expected: str) -> None:
        assert normalize_module_path(raw) == expected


# ----------------------------------------------------------------------
# 函数提取
# ----------------------------------------------------------------------
@pytest.fixture
def analyzer(tmp_path) -> ASTAnalyzer:
    return ASTAnalyzer(repo_path=str(tmp_path))


class TestParseSourceBasic:
    def test_extract_simple_function(self, analyzer: ASTAnalyzer) -> None:
        source = textwrap.dedent("""\
            def hello(x):
                return x + 1
        """)
        records = analyzer.parse_source(source, "apps/foo.py")
        assert len(records) == 1
        rec = records[0]
        assert rec.name == "hello"
        assert rec.qualified_name == "hello"
        assert rec.class_name == ""
        assert rec.is_async is False
        assert rec.is_action is False
        assert rec.signature == "apps.foo:hello"
        assert rec.start_line == 1
        assert rec.body_start_line == 1

    def test_async_function(self, analyzer: ASTAnalyzer) -> None:
        source = "async def health(req):\n    return None\n"
        records = analyzer.parse_source(source, "apps/foo.py")
        assert records[0].is_async is True
        assert records[0].name == "health"

    def test_decorator_shifts_start_line(self, analyzer: ASTAnalyzer) -> None:
        source = (
            "@property\n"           # line 1
            "def value(self):\n"    # line 2
            "    return 42\n"       # line 3
        )
        records = analyzer.parse_source(source, "apps/foo.py")
        assert records[0].start_line == 1     # 装饰器行
        assert records[0].body_start_line == 2  # def 行
        assert records[0].decorators == ("property",)
        assert records[0].covers(1) is True
        assert records[0].covers(3) is True

    def test_action_decorator_recognized(self, analyzer: ASTAnalyzer) -> None:
        source = textwrap.dedent("""\
            @action(detail=True, methods=["post"])
            def archive(self, request, pk=None):
                return None
        """)
        records = analyzer.parse_source(source, "apps/views.py")
        assert records[0].is_action is True
        assert "action" in records[0].decorators

    def test_class_methods_have_qualified_name(self, analyzer: ASTAnalyzer) -> None:
        source = textwrap.dedent("""\
            class ProjectViewSet:
                def list(self, request):
                    return None

                def create(self, request):
                    return None
        """)
        records = analyzer.parse_source(source, "apps/views.py")
        names = {r.qualified_name for r in records}
        assert names == {"ProjectViewSet.list", "ProjectViewSet.create"}
        for r in records:
            assert r.class_name == "ProjectViewSet"
            assert r.signature.startswith("apps.views:ProjectViewSet.")

    def test_nested_class(self, analyzer: ASTAnalyzer) -> None:
        source = textwrap.dedent("""\
            class Outer:
                class Inner:
                    def deep(self):
                        return 1
        """)
        records = analyzer.parse_source(source, "apps/foo.py")
        assert any(r.qualified_name == "Outer.Inner.deep" for r in records)

    def test_nested_function(self, analyzer: ASTAnalyzer) -> None:
        source = textwrap.dedent("""\
            def outer():
                def inner():
                    return 1
                return inner
        """)
        records = analyzer.parse_source(source, "apps/foo.py")
        names = {r.name for r in records}
        assert names == {"outer", "inner"}

    def test_invalid_syntax_returns_empty(self, analyzer: ASTAnalyzer) -> None:
        records = analyzer.parse_source("def broken(:\n", "apps/foo.py")
        assert records == []


# ----------------------------------------------------------------------
# 文件级 / 行号 → 函数签名
# ----------------------------------------------------------------------
class TestMapLinesToFunctions:
    def test_map_lines_basic(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(textwrap.dedent("""\
            def a():
                return 1

            def b():
                return 2
        """), encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        mapping = analyzer.map_lines_to_functions("apps/foo.py", [2, 5])
        assert mapping[2] == "apps.foo:a"
        assert mapping[5] == "apps.foo:b"

    def test_function_for_line_returns_record(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("def x():\n    return 1\n", encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        rec = analyzer.function_for_line("apps/foo.py", 2)
        assert isinstance(rec, FunctionRecord)
        assert rec.name == "x"

    def test_function_for_line_outside_returns_none(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("CONST = 1\n", encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        assert analyzer.function_for_line("apps/foo.py", 1) is None


# ----------------------------------------------------------------------
# diff → 变更函数
# ----------------------------------------------------------------------
class TestGetChangedFunctions:
    def test_changed_lines_resolve_to_functions(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(textwrap.dedent("""\
            def a():
                return 1

            def b():
                return 2
        """), encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))

        diff_result = {
            "changed_files": [
                {"path": "apps/foo.py", "added_lines": [2], "removed_lines": []},
            ]
        }
        recs = analyzer.get_changed_function_records(diff_result)
        assert len(recs) == 1
        assert recs[0].name == "a"

        # 旧版 dict API
        dicts = analyzer.get_changed_functions(diff_result)
        assert dicts[0]["name"] == "a"
        assert dicts[0]["signature"] == "apps.foo:a"

    def test_skips_missing_files(self, tmp_path) -> None:
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        diff_result = {
            "changed_files": [
                {"path": "apps/missing.py", "added_lines": [1], "removed_lines": []},
            ]
        }
        assert analyzer.get_changed_function_records(diff_result) == []

    def test_skips_non_python_files(self, tmp_path) -> None:
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        diff_result = {
            "changed_files": [
                {"path": "README.md", "added_lines": [1], "removed_lines": []},
            ]
        }
        assert analyzer.get_changed_function_records(diff_result) == []

    def test_dedup_signature(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("def a():\n    return 1\n    # tail\n", encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        diff_result = {
            "changed_files": [
                {"path": "apps/foo.py", "added_lines": [2, 3], "removed_lines": []},
            ]
        }
        recs = analyzer.get_changed_function_records(diff_result)
        assert len(recs) == 1


# ----------------------------------------------------------------------
# 兼容 API: _extract_functions
# ----------------------------------------------------------------------
class TestLegacyExtractFunctions:
    def test_returns_dict_list(self) -> None:
        source = "def foo():\n    return 1\n"
        result = ASTAnalyzer._extract_functions(source, "apps/foo.py")
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert result[0]["name"] == "foo"
        assert result[0]["signature"] == "apps.foo:foo"


# ----------------------------------------------------------------------
# 调用边: 行号 → caller signature
# ----------------------------------------------------------------------
class TestExtractCallEdges:
    def test_extract_calls_within_function(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "foo.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text(textwrap.dedent("""\
            def caller():
                return helper()

            def helper():
                return 1
        """), encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        edges = analyzer.extract_call_edges("apps/foo.py")
        # 至少存在一条 caller -> helper 边
        callers = {e.caller_signature for e in edges}
        callees = {e.callee_name for e in edges}
        assert "apps.foo:caller" in callers
        assert "helper" in callees

    def test_no_records_returns_empty(self, tmp_path) -> None:
        file_path = tmp_path / "apps" / "empty.py"
        file_path.parent.mkdir(parents=True)
        file_path.write_text("CONST = 1\n", encoding="utf-8")
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        assert analyzer.extract_call_edges("apps/empty.py") == []

    def test_missing_file_returns_empty(self, tmp_path) -> None:
        analyzer = ASTAnalyzer(repo_path=str(tmp_path))
        assert analyzer.extract_call_edges("apps/nope.py") == []


class TestFunctionRecordSerialization:
    def test_to_dict_round_trip(self, analyzer: ASTAnalyzer) -> None:
        records = analyzer.parse_source("def x():\n    pass\n", "apps/foo.py")
        d = records[0].to_dict()
        assert d["name"] == "x"
        assert d["module"] == "apps.foo"
        assert d["signature"] == "apps.foo:x"
        assert d["decorators"] == []
        assert d["lineno_def"] == d["body_start_line"]
