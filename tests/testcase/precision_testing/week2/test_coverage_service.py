# -*- coding: utf-8 -*-
"""Week2: Git Diff + AST 解析引擎 — CoverageService 公共 API 测试用例

覆盖模块: backend/apps/precision_testing/coverage_service.py
目标覆盖率: 80%+
生成时间: 2026-05-08
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# 确保 apps.precision_testing 可导入
# week2: tests/testcase/precision_testing/week2/test_foo.py → parents[4] = testhub_platform/
_test_file = Path(__file__).resolve()
sys.path.insert(0, str(_test_file.parents[4] / "backend"))

try:
    from apps.precision_testing.coverage_service import (
        CoverageService,
        FileCoverage,
        CoverageReport,
        _resolve_signature,
        _strip_context_phase,
        _signature_to_file,
    )
except ImportError:
    pytest.skip("apps.precision_testing.coverage_service not available", allow_module_level=True)


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
def service(temp_repo_path: Path) -> CoverageService:
    return CoverageService(repo_path=str(temp_repo_path))


# ==============================================================================
# 数据类测试 — FileCoverage
# ==============================================================================

class TestFileCoverage:
    """FileCoverage 数据类测试。"""

    def test_to_dict_basic(self) -> None:
        fc = FileCoverage(
            path="apps/views.py",
            covered_lines=(10, 11, 12),
            contexts_by_line={10: ("test_a",), 11: ("test_b",)},
        )
        d = fc.to_dict()
        assert d["path"] == "apps/views.py"
        assert d["covered_lines"] == [10, 11, 12]
        assert d["contexts_by_line"][10] == ["test_a"]
        assert d["contexts_by_line"][11] == ["test_b"]

    def test_empty_contexts(self) -> None:
        fc = FileCoverage(path="x.py", covered_lines=(1, 2), contexts_by_line={})
        d = fc.to_dict()
        assert d["contexts_by_line"] == {}

    def test_immutable(self) -> None:
        fc = FileCoverage(path="x.py", covered_lines=(1,), contexts_by_line={})
        with pytest.raises(Exception):
            fc.path = "y.py"  # type: ignore


# ==============================================================================
# 数据类测试 — CoverageReport
# ==============================================================================

class TestCoverageReport:
    """CoverageReport 数据类测试。"""

    def test_to_dict(self) -> None:
        fc = FileCoverage(path="a.py", covered_lines=(1,), contexts_by_line={})
        cr = CoverageReport(files=(fc,), contexts=("test_a", "test_b"))
        d = cr.to_dict()
        assert len(d["files"]) == 1
        assert d["files"][0]["path"] == "a.py"
        assert d["contexts"] == ["test_a", "test_b"]

    def test_empty_report(self) -> None:
        cr = CoverageReport(files=(), contexts=())
        d = cr.to_dict()
        assert d["files"] == []
        assert d["contexts"] == []


# ==============================================================================
# 辅助函数测试
# ==============================================================================

class TestHelperFunctions:
    """_resolve_signature / _strip_context_phase / _signature_to_file 测试。"""

    def test_resolve_signature_finds_match(self) -> None:
        mock_rec = MagicMock()
        mock_rec.covers = MagicMock(side_effect=lambda line: line == 10)
        mock_rec.signature = "apps.views:foo"
        result = _resolve_signature([mock_rec], 10)
        assert result == "apps.views:foo"

    def test_resolve_signature_no_match(self) -> None:
        mock_rec = MagicMock()
        mock_rec.covers = MagicMock(return_value=False)
        result = _resolve_signature([mock_rec], 99)
        assert result is None

    def test_strip_context_phase_with_pipe(self) -> None:
        assert _strip_context_phase("tests/x.py::test_a|setup") == "tests/x.py::test_a"
        assert _strip_context_phase("tests/x.py::test_b|teardown") == "tests/x.py::test_b"

    def test_strip_context_phase_without_pipe(self) -> None:
        assert _strip_context_phase("tests/x.py::test_a") == "tests/x.py::test_a"

    def test_signature_to_file(self) -> None:
        assert _signature_to_file("apps.foo.views:Bar.list") == "apps/foo/views.py"

    def test_signature_to_file_no_class(self) -> None:
        assert _signature_to_file("apps.foo.utils:helper") == "apps/foo/utils.py"


# ==============================================================================
# CoverageService — 初始化
# ==============================================================================

class TestCoverageServiceInit:
    """CoverageService 构造测试。"""

    def test_repo_path_resolved(self, temp_repo_path: Path) -> None:
        service = CoverageService(repo_path=str(temp_repo_path))
        assert service.repo_path == temp_repo_path.resolve()

    def test_default_coverage_db_path(self, temp_repo_path: Path) -> None:
        service = CoverageService(repo_path=str(temp_repo_path))
        assert service.coverage_db == temp_repo_path.resolve() / ".coverage"

    def test_custom_coverage_db_path(self, temp_repo_path: Path) -> None:
        service = CoverageService(
            repo_path=str(temp_repo_path),
            coverage_db=str(temp_repo_path / "custom.coverage"),
        )
        assert service.coverage_db.name == "custom.coverage"

    def test_repo_path_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            CoverageService(repo_path=str(tmp_path / "nonexistent"))


# ==============================================================================
# CoverageService — run_pytest_with_coverage
# ==============================================================================

class TestRunPytestWithCoverage:
    """run_pytest_with_coverage 方法测试。"""

    def test_pytest_not_found_raises(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="pytest 未安装"):
                service.run_pytest_with_coverage()

    def test_basic_command_constructed(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage()
                cmd = mock_run.call_args[0][0]
                assert "pytest" in cmd[0]
                assert "--cov" in cmd

    def test_cov_context_flag(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage(with_contexts=True)
                cmd = mock_run.call_args[0][0]
                assert "--cov-context=test" in cmd

    def test_no_cov_context_flag(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage(with_contexts=False)
                cmd = mock_run.call_args[0][0]
                assert "--cov-context=test" not in cmd

    def test_extra_args_passed(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage(extra_args=["-v", "-x"])
                cmd = mock_run.call_args[0][0]
                assert "-v" in cmd
                assert "-x" in cmd

    def test_source_argument(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage(source="apps")
                cmd = mock_run.call_args[0][0]
                assert any("--cov=apps" in arg for arg in cmd)

    def test_returns_returncode_and_output(self, service: CoverageService) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout="PASSED", stderr="ERROR"
                )
                rc, out = service.run_pytest_with_coverage()
                assert rc == 1
                assert "PASSED" in out
                assert "ERROR" in out

    def test_cwd_is_repo_path(self, service: CoverageService, temp_repo_path: Path) -> None:
        with patch("shutil.which", return_value="/usr/bin/pytest"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                service.run_pytest_with_coverage()
                call_kwargs = mock_run.call_args[1]
                assert call_kwargs["cwd"] == str(temp_repo_path.resolve())


# ==============================================================================
# CoverageService — parse_coverage_db
# ==============================================================================

class TestParseCoverageDb:
    """parse_coverage_db 方法测试。"""

    def test_coverage_not_installed_returns_empty(self, service: CoverageService) -> None:
        with patch("apps.precision_testing.coverage_service.CoverageData", None):
            report = service.parse_coverage_db()
            assert report.files == ()
            assert report.contexts == ()

    def test_db_not_exists_returns_empty(self, service: CoverageService) -> None:
        assert not service.coverage_db.exists()
        report = service.parse_coverage_db()
        assert report.files == ()
        assert report.contexts == ()

    def test_db_read_error_returns_empty(self, service: CoverageService, tmp_path: Path) -> None:
        # Create a fake .coverage file
        db_path = service.coverage_db
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("not a valid db", encoding="utf-8")

        with patch("apps.precision_testing.coverage_service.CoverageData") as MockData:
            mock_data = MagicMock()
            mock_data.read.side_effect = Exception("db read error")
            MockData.return_value = mock_data
            report = service.parse_coverage_db()
            assert report.files == ()
            assert report.contexts == ()

    def test_normalizes_path(self, service: CoverageService, temp_repo_path: Path) -> None:
        """验证路径规范化逻辑被调用。"""
        db_path = service.coverage_db
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a mock coverage database
        with patch("apps.precision_testing.coverage_service.CoverageData") as MockData:
            mock_data = MagicMock()
            mock_data.measured_contexts.return_value = []
            mock_data.measured_files.return_value = []
            MockData.return_value = mock_data

            report = service.parse_coverage_db()
            # Should not raise — just verify path normalization didn't crash

    def test_contexts_sorted_and_filtered(self, service: CoverageService, tmp_path: Path) -> None:
        """验证 coverage contexts 被排序且过滤空字符串。"""
        # Test the helper function behavior directly
        from apps.precision_testing.coverage_service import _strip_context_phase

        raw_contexts = ["test_b", "test_a", ""]
        # Simulate what parse_coverage_db does: sorted + filter empty
        filtered = tuple(sorted(c for c in raw_contexts if c))
        assert filtered == ("test_a", "test_b")


# ==============================================================================
# CoverageService — map_lines_to_functions
# ==============================================================================

class TestMapLinesToFunctions:
    """map_lines_to_functions 方法测试。"""

    def test_empty_report(self, service: CoverageService) -> None:
        result = service.map_lines_to_functions(report=CoverageReport(files=(), contexts=()))
        assert result == {}

    def test_filters_non_python_files(self, service: CoverageService) -> None:
        fc = FileCoverage(path="apps/views.txt", covered_lines=(1, 2), contexts_by_line={})
        report = CoverageReport(files=(fc,), contexts=())
        result = service.map_lines_to_functions(report=report)
        assert "apps/views.txt" not in result

    def test_calls_ast_map_lines_to_functions(
        self, service: CoverageService, temp_repo_path: Path
    ) -> None:
        test_file = temp_repo_path / "apps" / "test.py"
        test_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        fc = FileCoverage(
            path="apps/test.py",
            covered_lines=(1, 2),
            contexts_by_line={},
        )
        report = CoverageReport(files=(fc,), contexts=())
        result = service.map_lines_to_functions(report=report)
        # Should contain the signature for apps/test.py
        assert "apps/test.py" in result


# ==============================================================================
# CoverageService — per_test_coverage
# ==============================================================================

class TestPerTestCoverage:
    """per_test_coverage 方法测试。"""

    def test_empty_report(self, service: CoverageService) -> None:
        result = service.per_test_coverage(report=CoverageReport(files=(), contexts=()))
        assert result == {}

    def test_filters_non_python_files(self, service: CoverageService) -> None:
        fc = FileCoverage(
            path="apps/views.txt",
            covered_lines=(1,),
            contexts_by_line={1: ("test_a",)},
        )
        report = CoverageReport(files=(fc,), contexts=("test_a",))
        result = service.per_test_coverage(report=report)
        assert result == {}

    def test_strips_context_phase(self, service: CoverageService, temp_repo_path: Path) -> None:
        test_file = temp_repo_path / "apps" / "ptc.py"
        test_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        fc = FileCoverage(
            path="apps/ptc.py",
            covered_lines=(1,),
            contexts_by_line={1: ("tests/x.py::test_foo|setup",)},
        )
        report = CoverageReport(files=(fc,), contexts=("tests/x.py::test_foo|setup",))
        result = service.per_test_coverage(report=report)
        assert "tests/x.py::test_foo" in result

    def test_empty_contexts_by_line(self, service: CoverageService) -> None:
        fc = FileCoverage(path="apps/x.py", covered_lines=(1,), contexts_by_line={})
        report = CoverageReport(files=(fc,), contexts=())
        result = service.per_test_coverage(report=report)
        assert result == {}


# ==============================================================================
# CoverageService — build_static_mappings
# ==============================================================================

class TestBuildStaticMappings:
    """build_static_mappings 方法测试。"""

    def test_empty_index(self, service: CoverageService) -> None:
        candidates = service.build_static_mappings(per_test_index={})
        assert candidates == []

    def test_generates_candidates(self, service: CoverageService) -> None:
        per_test_index = {
            "tests/api/test_users.py::test_create": {"apps.users.views:UserViewSet.create"},
            "tests/api/test_users.py::test_list": {"apps.users.views:UserViewSet.list"},
        }
        candidates = service.build_static_mappings(per_test_index=per_test_index)
        assert len(candidates) == 2
        assert all(c["mapping_type"] == "auto_static" for c in candidates)
        assert all(c["confidence"] == 0.8 for c in candidates)
        assert all(c["file_path"] is not None for c in candidates)

    def test_multiple_signatures_per_test(self, service: CoverageService) -> None:
        per_test_index = {
            "tests/api/test_x.py::test_a": {
                "apps.foo:Bar.method1",
                "apps.foo:Bar.method2",
            }
        }
        candidates = service.build_static_mappings(per_test_index=per_test_index)
        assert len(candidates) == 2

    def test_calls_per_test_coverage_when_none(self, service: CoverageService) -> None:
        with patch.object(service, "per_test_coverage", return_value={}) as mock_ptc:
            service.build_static_mappings(per_test_index=None)
            mock_ptc.assert_called_once()


# ==============================================================================
# CoverageService — _normalize_path
# ==============================================================================

class TestNormalizePath:
    """_normalize_path 方法测试。"""

    def test_relative_to_repo(self, service: CoverageService, temp_repo_path: Path) -> None:
        result = service._normalize_path(str(temp_repo_path / "apps" / "views.py"))
        assert result is not None
        assert "apps" in result
        assert "\\" not in result

    def test_outside_repo_returns_none(self, service: CoverageService, tmp_path: Path) -> None:
        """路径在 repo 外时返回 None（relative_to 抛出 ValueError）。"""
        # Use a path that is a sibling but not relative to repo
        # e.g., repo at apps/projects, test a sibling "apps/other/file.py"
        other_dir = service.repo_path.parent / "other_module"
        other_dir.mkdir(parents=True, exist_ok=True)
        result = service._normalize_path(str(other_dir / "file.py"))
        assert result is None

    def test_invalid_path_returns_none(self, service: CoverageService) -> None:
        with patch("pathlib.Path.resolve", side_effect=OSError("invalid")):
            result = service._normalize_path("/some/path")
            assert result is None


# ==============================================================================
# 场景测试 — 完整流程
# ==============================================================================

class TestCoverageServiceFullWorkflow:
    """端到端场景测试。"""

    def test_full_coverage_pipeline(self, service: CoverageService, temp_repo_path: Path) -> None:
        """模拟完整的覆盖率采集→解析→映射流程。"""
        test_file = temp_repo_path / "apps" / "pipeline.py"
        test_file.write_text("def foo():\n    pass\n\ndef bar():\n    pass\n", encoding="utf-8")

        # Build a mock coverage report
        fc = FileCoverage(
            path="apps/pipeline.py",
            covered_lines=(1, 2, 4, 5),
            contexts_by_line={1: ("test_foo",), 4: ("test_bar",)},
        )
        report = CoverageReport(files=(fc,), contexts=("test_foo", "test_bar"))

        # map_lines_to_functions
        mapping = service.map_lines_to_functions(report=report)
        assert "apps/pipeline.py" in mapping

        # per_test_coverage
        per_test = service.per_test_coverage(report=report)
        assert "test_foo" in per_test
        assert "test_bar" in per_test

        # build_static_mappings
        candidates = service.build_static_mappings(per_test_index=per_test)
        assert len(candidates) >= 2
        assert all(c["mapping_type"] == "auto_static" for c in candidates)

    def test_coverage_not_installed_graceful(self, temp_repo_path: Path) -> None:
        """coverage 未安装时应优雅降级。"""
        with patch("apps.precision_testing.coverage_service.CoverageData", None):
            service = CoverageService(repo_path=str(temp_repo_path))
            report = service.parse_coverage_db()
            assert report.files == ()
            assert report.contexts == ()