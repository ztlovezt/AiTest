"""CoverageService 单元测试。

通过 ``coverage.CoverageData`` 公共 API 直接构造 ``.coverage`` 数据库,
不依赖真实 pytest 执行,使测试可在沙箱内确定性地运行。

覆盖目标:
    * ``parse_coverage_db`` 解析 (含/不含 contexts)
    * ``map_lines_to_functions``: 行号 → 函数签名
    * ``per_test_coverage``: dynamic context → test_id 映射
    * ``build_static_mappings``: 候选 TestCaseCodeMapping
    * ``_strip_context_phase`` / ``_signature_to_file`` / 路径规范化
    * 缺库 / 缺数据库的容错
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from apps.precision_testing.coverage_service import (
    CoverageReport,
    CoverageService,
    FileCoverage,
    _resolve_signature,
    _signature_to_file,
    _strip_context_phase,
)

coverage = pytest.importorskip("coverage")


# ----------------------------------------------------------------------
# 模块级辅助
# ----------------------------------------------------------------------
class TestSimpleHelpers:
    @pytest.mark.parametrize("ctx,expected", [
        ("tests/x.py::test_a|setup", "tests/x.py::test_a"),
        ("tests/x.py::test_a|run", "tests/x.py::test_a"),
        ("tests/x.py::test_a", "tests/x.py::test_a"),
        ("", ""),
    ])
    def test_strip_context_phase(self, ctx: str, expected: str) -> None:
        assert _strip_context_phase(ctx) == expected

    def test_signature_to_file(self) -> None:
        assert _signature_to_file("apps.foo.views:Bar.list") == "apps/foo/views.py"
        assert _signature_to_file("apps.foo:func") == "apps/foo.py"


class TestFileCoverageDataclass:
    def test_to_dict(self) -> None:
        fc = FileCoverage(
            path="apps/foo.py",
            covered_lines=(1, 2, 3),
            contexts_by_line={2: ("tests/test_foo.py::test_a",)},
        )
        d = fc.to_dict()
        assert d["path"] == "apps/foo.py"
        assert d["covered_lines"] == [1, 2, 3]
        assert d["contexts_by_line"] == {2: ["tests/test_foo.py::test_a"]}

    def test_coverage_report_to_dict(self) -> None:
        report = CoverageReport(
            files=(FileCoverage(path="x.py", covered_lines=(1,)),),
            contexts=("ctx1",),
        )
        d = report.to_dict()
        assert d["contexts"] == ["ctx1"]
        assert d["files"][0]["path"] == "x.py"


# ----------------------------------------------------------------------
# fixture: 生成最小 coverage 数据库
# ----------------------------------------------------------------------
@pytest.fixture
def repo_with_source(tmp_path) -> Path:
    """构造仓库 + 一个含两个函数的目标 Python 文件。

    仓库根固定在 ``tmp_path/repo``,这样 ``tmp_path`` 下其它目录可作为"仓库外"路径。
    """
    repo = tmp_path / "repo"
    src = repo / "apps" / "foo.py"
    src.parent.mkdir(parents=True)
    src.write_text(textwrap.dedent("""\
        def alpha():
            return 1


        def beta():
            return 2
    """), encoding="utf-8")
    return repo


def _write_coverage_db(
    repo_path: Path,
    file_path: Path,
    *,
    contexts_to_lines: dict[str, list[int]] | None = None,
    plain_lines: list[int] | None = None,
) -> Path:
    """用公共 API 写一个 .coverage 数据库。"""
    db = repo_path / ".coverage"
    data = coverage.CoverageData(basename=str(db))
    abs_path = str(file_path.resolve())
    if plain_lines:
        data.set_context("")
        data.add_lines({abs_path: plain_lines})
    if contexts_to_lines:
        for ctx, lines in contexts_to_lines.items():
            data.set_context(ctx)
            data.add_lines({abs_path: lines})
    data.write()
    return db


# ----------------------------------------------------------------------
# parse_coverage_db
# ----------------------------------------------------------------------
class TestParseCoverageDb:
    def test_no_db_returns_empty_report(self, tmp_path) -> None:
        svc = CoverageService(repo_path=str(tmp_path))
        report = svc.parse_coverage_db()
        assert report.files == ()
        assert report.contexts == ()

    def test_parse_plain_lines(self, repo_with_source) -> None:
        target = repo_with_source / "apps" / "foo.py"
        _write_coverage_db(repo_with_source, target, plain_lines=[1, 2, 5, 6])

        svc = CoverageService(repo_path=str(repo_with_source))
        report = svc.parse_coverage_db(with_contexts=False)
        assert len(report.files) == 1
        fc = report.files[0]
        assert fc.path == "apps/foo.py"
        assert set(fc.covered_lines) >= {1, 2, 5, 6}

    def test_parse_with_contexts(self, repo_with_source) -> None:
        target = repo_with_source / "apps" / "foo.py"
        _write_coverage_db(
            repo_with_source,
            target,
            contexts_to_lines={
                "tests/test_foo.py::test_alpha|run": [1, 2],
                "tests/test_foo.py::test_beta|run": [5, 6],
            },
        )
        svc = CoverageService(repo_path=str(repo_with_source))
        report = svc.parse_coverage_db(with_contexts=True)
        assert len(report.files) == 1
        fc = report.files[0]
        assert fc.contexts_by_line  # 至少有一行被某 context 覆盖


# ----------------------------------------------------------------------
# map_lines_to_functions
# ----------------------------------------------------------------------
class TestMapLinesToFunctions:
    def test_lines_resolve_to_signatures(self, repo_with_source) -> None:
        target = repo_with_source / "apps" / "foo.py"
        _write_coverage_db(repo_with_source, target, plain_lines=[1, 2, 5, 6])

        svc = CoverageService(repo_path=str(repo_with_source))
        result = svc.map_lines_to_functions()
        assert "apps/foo.py" in result
        sigs = result["apps/foo.py"]
        assert "apps.foo:alpha" in sigs
        assert "apps.foo:beta" in sigs


# ----------------------------------------------------------------------
# per_test_coverage / build_static_mappings
# ----------------------------------------------------------------------
class TestPerTestCoverage:
    def test_dynamic_context_to_test_id(self, repo_with_source) -> None:
        target = repo_with_source / "apps" / "foo.py"
        _write_coverage_db(
            repo_with_source,
            target,
            contexts_to_lines={
                "tests/test_foo.py::test_alpha|run": [1, 2],
                "tests/test_foo.py::test_beta|run": [5, 6],
            },
        )
        svc = CoverageService(repo_path=str(repo_with_source))
        per_test = svc.per_test_coverage()
        assert "tests/test_foo.py::test_alpha" in per_test
        assert "apps.foo:alpha" in per_test["tests/test_foo.py::test_alpha"]
        assert "apps.foo:beta" in per_test["tests/test_foo.py::test_beta"]

    def test_build_static_mappings(self, repo_with_source) -> None:
        target = repo_with_source / "apps" / "foo.py"
        _write_coverage_db(
            repo_with_source,
            target,
            contexts_to_lines={
                "tests/test_foo.py::test_alpha|run": [1, 2],
            },
        )
        svc = CoverageService(repo_path=str(repo_with_source))
        candidates = svc.build_static_mappings()
        assert candidates
        candidate = candidates[0]
        assert candidate["mapping_type"] == "auto_static"
        assert candidate["confidence"] == 0.8
        assert candidate["file_path"] == "apps/foo.py"
        assert candidate["test_id"] == "tests/test_foo.py::test_alpha"


# ----------------------------------------------------------------------
# 路径规范化 / 异常
# ----------------------------------------------------------------------
class TestNormalizePath:
    def test_outside_repo_returns_none(self, repo_with_source, tmp_path) -> None:
        svc = CoverageService(repo_path=str(repo_with_source))
        # 仓库外的路径
        outside = tmp_path / "other_repo" / "x.py"
        outside.parent.mkdir(parents=True)
        outside.write_text("x = 1\n", encoding="utf-8")
        assert svc._normalize_path(str(outside)) is None

    def test_inside_repo_returns_relative(self, repo_with_source) -> None:
        svc = CoverageService(repo_path=str(repo_with_source))
        target = (repo_with_source / "apps" / "foo.py").resolve()
        assert svc._normalize_path(str(target)) == "apps/foo.py"


class TestInitErrors:
    def test_missing_repo_path(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            CoverageService(repo_path=str(tmp_path / "nope"))


class TestResolveSignatureHelper:
    def test_resolves_line_to_signature(self, repo_with_source) -> None:
        from apps.precision_testing.ast_analyzer import ASTAnalyzer

        ast_an = ASTAnalyzer(str(repo_with_source))
        records = ast_an.parse_file("apps/foo.py")
        # alpha 第 1-2 行,beta 第 5-6 行
        assert _resolve_signature(records, 2) == "apps.foo:alpha"
        assert _resolve_signature(records, 6) == "apps.foo:beta"
        assert _resolve_signature(records, 100) is None
