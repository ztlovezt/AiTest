"""GitDiffAnalyzer 单元测试。

覆盖目标:
    * diff 文本解析: 增/删/修改/重命名
    * 行号区间合并 ``_lines_to_ranges``
    * 路径规范化 (Windows backslash, ``a/`` ``b/`` 前缀)
    * commit 元数据 / 默认分支推断 / 历史快照
    * excluded_dirs 过滤
"""
from __future__ import annotations

import pytest

from apps.precision_testing.git_analyzer import (
    DiffStats,
    FileChange,
    GitDiffAnalyzer,
    LineRange,
    _DEFAULT_EXCLUDED_DIRS,
)


# ----------------------------------------------------------------------
# 纯函数 / dataclass 行为
# ----------------------------------------------------------------------
class TestLineRangeAndStats:
    def test_line_range_to_tuple(self) -> None:
        r = LineRange(10, 20)
        assert r.to_tuple() == (10, 20)

    def test_line_range_contains(self) -> None:
        r = LineRange(5, 10)
        assert r.contains(5)
        assert r.contains(10)
        assert not r.contains(4)
        assert not r.contains(11)

    def test_diff_stats_to_dict(self) -> None:
        stats = DiffStats(files=3, additions=10, deletions=4)
        assert stats.to_dict() == {"files": 3, "additions": 10, "deletions": 4}

    def test_default_excluded_dirs_contains_common(self) -> None:
        for name in {"__pycache__", "migrations", "node_modules"}:
            assert name in _DEFAULT_EXCLUDED_DIRS


class TestLinesToRanges:
    def test_empty(self) -> None:
        assert GitDiffAnalyzer._lines_to_ranges(()) == ()

    def test_single_line(self) -> None:
        ranges = GitDiffAnalyzer._lines_to_ranges((7,))
        assert [r.to_tuple() for r in ranges] == [(7, 7)]

    def test_consecutive_merge(self) -> None:
        ranges = GitDiffAnalyzer._lines_to_ranges((3, 4, 5))
        assert [r.to_tuple() for r in ranges] == [(3, 5)]

    def test_multiple_intervals(self) -> None:
        ranges = GitDiffAnalyzer._lines_to_ranges((3, 4, 5, 8, 9, 12))
        assert [r.to_tuple() for r in ranges] == [(3, 5), (8, 9), (12, 12)]


class TestNormalizePath:
    @pytest.mark.parametrize("raw,expected", [
        ("a/apps/foo.py", "apps/foo.py"),
        ("b/apps/foo.py", "apps/foo.py"),
        ("./apps/foo.py", "apps/foo.py"),
        ("apps\\foo.py", "apps/foo.py"),
        ("apps/foo.py", "apps/foo.py"),
        ("  apps/foo.py  ", "apps/foo.py"),
    ])
    def test_normalizes(self, raw: str, expected: str) -> None:
        assert GitDiffAnalyzer._normalize_path(raw) == expected


class TestFileChangeSerialization:
    def test_to_dict(self) -> None:
        fc = FileChange(
            path="apps/foo.py",
            change_type="modified",
            added_lines=(10, 11),
            removed_lines=(5,),
            added_ranges=(LineRange(10, 11),),
            removed_ranges=(LineRange(5, 5),),
            is_python=True,
        )
        d = fc.to_dict()
        assert d["path"] == "apps/foo.py"
        assert d["added_lines"] == [10, 11]
        assert d["removed_lines"] == [5]
        assert d["added_ranges"] == [[10, 11]]
        assert d["removed_ranges"] == [[5, 5]]
        assert d["is_python"] is True


class TestExcludedDirs:
    def test_excluded_filter(self, tmp_path) -> None:
        from git import Actor, Repo

        repo_path = tmp_path / "exrepo"
        repo_path.mkdir()
        Repo.init(str(repo_path), initial_branch="main")
        analyzer = GitDiffAnalyzer(str(repo_path))
        assert analyzer._is_excluded("apps/__pycache__/foo.py")
        assert analyzer._is_excluded("apps/migrations/0001.py")
        assert not analyzer._is_excluded("apps/foo.py")


# ----------------------------------------------------------------------
# 集成: 真实 git 仓库 diff
# ----------------------------------------------------------------------
@pytest.fixture
def two_commit_repo(make_git_repo):
    """构造一个两 commit 仓库: 第一次新增 foo.py, 第二次修改若干行。"""
    initial = (
        "def a():\n"
        "    return 1\n"
        "\n"
        "def b():\n"
        "    return 2\n"
    )
    modified = (
        "def a():\n"
        "    return 100  # changed\n"
        "\n"
        "def b():\n"
        "    return 2\n"
        "\n"
        "def c():\n"
        "    return 3\n"
    )
    return make_git_repo([
        ("apps/foo.py", initial),
        ("apps/foo.py", modified),
    ])


class TestDiffStructured:
    def test_diff_detects_modified_python_file(self, two_commit_repo) -> None:
        repo_path, base, head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        result = analyzer.get_diff_structured(base, head)
        assert result.base == base
        assert result.head == head
        assert len(result.files) == 1
        fc = result.files[0]
        assert fc.path == "apps/foo.py"
        assert fc.is_python is True
        assert fc.change_type == "modified"
        # 必有新增行,且至少包含一段连续区间
        assert fc.added_lines
        assert fc.added_ranges

    def test_diff_dict_format_backward_compat(self, two_commit_repo) -> None:
        repo_path, base, head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        d = analyzer.get_diff(base, head)
        assert "stats" in d and "changed_files" in d
        assert d["stats"]["files"] == 1
        assert d["changed_files"][0]["is_python"] is True

    def test_python_files_filter(self, make_git_repo) -> None:
        repo_path, base, head = make_git_repo([
            ("apps/foo.py", "x = 1\n"),
            ("README.md", "# title\n"),
            ("apps/foo.py", "x = 2\n"),
        ])
        analyzer = GitDiffAnalyzer(str(repo_path))
        py_changes = analyzer.get_python_changes(base, head)
        assert len(py_changes) == 1
        assert py_changes[0].path == "apps/foo.py"

    def test_changed_files_paths_list(self, two_commit_repo) -> None:
        repo_path, base, head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        assert analyzer.get_changed_files(base, head) == ["apps/foo.py"]


class TestRepoMetadata:
    def test_get_commit_info_fields(self, two_commit_repo) -> None:
        repo_path, _base, head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        info = analyzer.get_commit_info(head)
        assert info["sha"] == head
        assert info["short_sha"] == head[:7]
        assert info["author"] == "Tester"
        assert "committed_datetime" in info
        assert isinstance(info["parents"], list)

    def test_list_recent_commits(self, two_commit_repo) -> None:
        repo_path, _base, _head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        commits = analyzer.list_recent_commits(branch="main", limit=10)
        assert len(commits) == 2
        for c in commits:
            assert "sha" in c and "author" in c

    def test_default_branch(self, two_commit_repo) -> None:
        repo_path, _base, _head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        assert analyzer.get_default_branch() == "main"

    def test_get_file_at_commit(self, two_commit_repo) -> None:
        repo_path, base, _head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        content = analyzer.get_file_at_commit("apps/foo.py", base)
        assert content is not None
        assert "def a()" in content

    def test_get_file_at_commit_missing(self, two_commit_repo) -> None:
        repo_path, base, _head = two_commit_repo
        analyzer = GitDiffAnalyzer(str(repo_path))
        assert analyzer.get_file_at_commit("not_exist.py", base) is None


class TestInitErrors:
    def test_repo_path_missing(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            GitDiffAnalyzer(str(tmp_path / "does_not_exist"))

    def test_not_a_git_repo(self, tmp_path) -> None:
        non_repo = tmp_path / "nope"
        non_repo.mkdir()
        with pytest.raises(ValueError):
            GitDiffAnalyzer(str(non_repo))
