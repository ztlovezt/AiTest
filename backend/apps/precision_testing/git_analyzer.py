"""Git 差异解析器 — GitPython + unidiff

负责从 Git 仓库中提取 base..head 区间的文件变更与行号信息,
并将连续行号合并为区间,供 AST 分析阶段定位变更函数。

输出结构(JSON 可序列化):
    {
        "base": "<sha>",
        "head": "<sha>",
        "stats": {"files": 3, "additions": 42, "deletions": 7},
        "changed_files": [
            {
                "path": "apps/projects/views.py",
                "old_path": null,
                "change_type": "modified",
                "added_lines": [42, 43, 44],
                "removed_lines": [40],
                "added_ranges": [[42, 44]],
                "removed_ranges": [[40, 40]],
                "is_python": true,
            }
        ]
    }
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    from git import Repo
    from git.exc import GitCommandError, InvalidGitRepositoryError
except ImportError:  # pragma: no cover - 防御导入
    Repo = None  # type: ignore[assignment]
    GitCommandError = Exception  # type: ignore[assignment,misc]
    InvalidGitRepositoryError = Exception  # type: ignore[assignment,misc]

try:
    from unidiff import PatchSet
except ImportError:  # pragma: no cover
    PatchSet = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# 默认排除的目录(测试夹具/构建产物等无需进入图谱)
_DEFAULT_EXCLUDED_DIRS: frozenset[str] = frozenset({
    "__pycache__",
    "migrations",
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "static_files",
    "static",
    "media",
    "logs",
    "docs",
    "expand",
})


@dataclass(frozen=True)
class LineRange:
    """连续行号区间(闭区间)。"""
    start: int
    end: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.start, self.end)

    def contains(self, line: int) -> bool:
        return self.start <= line <= self.end


@dataclass(frozen=True)
class FileChange:
    """单个文件的变更摘要。"""
    path: str
    change_type: str  # 'added' | 'removed' | 'modified' | 'renamed'
    added_lines: tuple[int, ...] = ()
    removed_lines: tuple[int, ...] = ()
    added_ranges: tuple[LineRange, ...] = ()
    removed_ranges: tuple[LineRange, ...] = ()
    old_path: str | None = None
    is_python: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "old_path": self.old_path,
            "change_type": self.change_type,
            "added_lines": list(self.added_lines),
            "removed_lines": list(self.removed_lines),
            "added_ranges": [list(r.to_tuple()) for r in self.added_ranges],
            "removed_ranges": [list(r.to_tuple()) for r in self.removed_ranges],
            "is_python": self.is_python,
        }


@dataclass(frozen=True)
class DiffStats:
    files: int = 0
    additions: int = 0
    deletions: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"files": self.files, "additions": self.additions, "deletions": self.deletions}


@dataclass(frozen=True)
class DiffResult:
    base: str
    head: str
    stats: DiffStats = field(default_factory=DiffStats)
    files: tuple[FileChange, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "base": self.base,
            "head": self.head,
            "stats": self.stats.to_dict(),
            "changed_files": [f.to_dict() for f in self.files],
        }

    def python_files(self) -> tuple[FileChange, ...]:
        return tuple(f for f in self.files if f.is_python)


class GitDiffAnalyzer:
    """解析 Git 仓库的 commit range diff,提取变更文件和行号区间。"""

    def __init__(
        self,
        repo_path: str,
        excluded_dirs: Iterable[str] | None = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path does not exist: {repo_path}")
        if Repo is None:
            raise RuntimeError("GitPython 未安装,无法初始化 GitDiffAnalyzer")

        try:
            self._repo = Repo(str(self.repo_path), search_parent_directories=True)
        except InvalidGitRepositoryError as exc:
            raise ValueError(f"路径不是合法的 Git 仓库: {repo_path}") from exc

        self._excluded_dirs = frozenset(excluded_dirs) if excluded_dirs else _DEFAULT_EXCLUDED_DIRS

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def get_diff(self, base: str, head: str) -> dict[str, Any]:
        """获取 base..head 的 diff 结构化结果(JSON 可序列化字典)。"""
        result = self.get_diff_structured(base, head)
        return result.to_dict()

    def get_diff_structured(self, base: str, head: str) -> DiffResult:
        """获取 base..head 的 diff,返回结构化对象(便于内部消费)。"""
        if PatchSet is None:
            logger.warning("unidiff 未安装,返回空 diff")
            return DiffResult(base=base, head=head)

        try:
            base_resolved = self._resolve_revision(base)
            head_resolved = self._resolve_revision(head)
        except GitCommandError as exc:
            logger.warning("无法解析 commit (%s vs %s): %s", base, head, exc)
            return DiffResult(base=base, head=head)

        try:
            diff_text = self._repo.git.diff(
                base_resolved, head_resolved,
                unified=0,
                no_color=True,
                find_renames=True,
            )
        except GitCommandError as exc:
            logger.warning("git diff 失败 (%s vs %s): %s", base, head, exc)
            return DiffResult(base=base_resolved, head=head_resolved)

        files = self._parse_diff_text(diff_text)
        # 过滤被排除目录
        files = tuple(f for f in files if not self._is_excluded(f.path))
        stats = self._compute_stats(files)
        return DiffResult(base=base_resolved, head=head_resolved, stats=stats, files=files)

    def get_changed_files(self, base: str, head: str) -> list[str]:
        """仅返回变更文件路径列表(去重、规范化)。"""
        result = self.get_diff_structured(base, head)
        return [f.path for f in result.files]

    def get_python_changes(self, base: str, head: str) -> list[FileChange]:
        """只返回 Python 文件的变更(供 AST 分析使用)。"""
        return list(self.get_diff_structured(base, head).python_files())

    def get_commit_info(self, sha: str) -> dict[str, Any]:
        """获取单个 commit 的元数据(作者/时间/消息/父提交)。"""
        commit = self._repo.commit(self._resolve_revision(sha))
        return {
            "sha": commit.hexsha,
            "short_sha": commit.hexsha[:7],
            "author": commit.author.name,
            "author_email": commit.author.email,
            "committed_datetime": commit.committed_datetime.isoformat(),
            "message": commit.message.strip(),
            "parents": [p.hexsha for p in commit.parents],
        }

    def list_recent_commits(self, branch: str = "HEAD", limit: int = 20) -> list[dict[str, Any]]:
        """列出某分支最近 N 个 commit(供前端选择 base/head)。"""
        commits = []
        try:
            for commit in self._repo.iter_commits(branch, max_count=limit):
                commits.append({
                    "sha": commit.hexsha,
                    "short_sha": commit.hexsha[:7],
                    "author": commit.author.name,
                    "committed_datetime": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip().split("\n", 1)[0],
                })
        except GitCommandError as exc:
            logger.warning("列出 commit 失败 (%s): %s", branch, exc)
        return commits

    def get_default_branch(self) -> str:
        """猜测仓库默认分支(优先 main,其次 master,fallback 当前 HEAD)。"""
        for candidate in ("main", "master"):
            try:
                self._repo.commit(candidate)
                return candidate
            except (GitCommandError, ValueError, Exception):
                # ValueError: rev does not exist as valid ref
                # Exception: covers gitdb.exc.BadName and other git exceptions
                continue
        try:
            return self._repo.active_branch.name
        except TypeError:
            return "HEAD"

    def get_file_at_commit(self, path: str, sha: str) -> str | None:
        """读取某个 commit 时刻的文件内容(用于历史对比)。"""
        try:
            blob = self._repo.commit(self._resolve_revision(sha)).tree / path
            return blob.data_stream.read().decode("utf-8", errors="replace")
        except (KeyError, GitCommandError):
            return None

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _resolve_revision(self, rev: str) -> str:
        """将 'HEAD'/'HEAD~1'/short-sha 等修订引用解析为完整 SHA。"""
        return self._repo.git.rev_parse(rev).strip()

    @staticmethod
    def _parse_diff_text(diff_text: str) -> tuple[FileChange, ...]:
        if not diff_text:
            return ()

        patch = PatchSet.from_string(diff_text)
        changes: list[FileChange] = []
        for patched_file in patch:
            change_type = GitDiffAnalyzer._infer_change_type(patched_file)
            added: list[int] = []
            removed: list[int] = []
            for hunk in patched_file:
                for line in hunk:
                    if line.is_added and line.target_line_no is not None:
                        added.append(line.target_line_no)
                    elif line.is_removed and line.source_line_no is not None:
                        removed.append(line.source_line_no)
            path = GitDiffAnalyzer._normalize_path(patched_file.path)
            old_path = (
                GitDiffAnalyzer._normalize_path(patched_file.source_file.lstrip("ab/"))
                if patched_file.is_rename else None
            )
            added_sorted = tuple(sorted(set(added)))
            removed_sorted = tuple(sorted(set(removed)))
            changes.append(FileChange(
                path=path,
                old_path=old_path,
                change_type=change_type,
                added_lines=added_sorted,
                removed_lines=removed_sorted,
                added_ranges=GitDiffAnalyzer._lines_to_ranges(added_sorted),
                removed_ranges=GitDiffAnalyzer._lines_to_ranges(removed_sorted),
                is_python=path.endswith(".py"),
            ))
        return tuple(changes)

    @staticmethod
    def _infer_change_type(patched_file: Any) -> str:
        if getattr(patched_file, "is_added_file", False):
            return "added"
        if getattr(patched_file, "is_removed_file", False):
            return "removed"
        if getattr(patched_file, "is_rename", False):
            return "renamed"
        return "modified"

    @staticmethod
    def _normalize_path(raw: str) -> str:
        """统一为正斜杠相对路径,去除 a/ b/ 前缀。"""
        path = raw.replace("\\", "/").strip()
        for prefix in ("a/", "b/", "./"):
            if path.startswith(prefix):
                path = path[len(prefix):]
        return path

    @staticmethod
    def _lines_to_ranges(lines: tuple[int, ...]) -> tuple[LineRange, ...]:
        """将有序行号合并为连续区间,例如 [3,4,5,8,9] → [(3,5),(8,9)]。"""
        if not lines:
            return ()
        ranges: list[LineRange] = []
        start = prev = lines[0]
        for line in lines[1:]:
            if line == prev + 1:
                prev = line
                continue
            ranges.append(LineRange(start, prev))
            start = prev = line
        ranges.append(LineRange(start, prev))
        return tuple(ranges)

    def _is_excluded(self, path: str) -> bool:
        parts = path.split("/")
        return any(part in self._excluded_dirs for part in parts)

    @staticmethod
    def _compute_stats(files: tuple[FileChange, ...]) -> DiffStats:
        return DiffStats(
            files=len(files),
            additions=sum(len(f.added_lines) for f in files),
            deletions=sum(len(f.removed_lines) for f in files),
        )
