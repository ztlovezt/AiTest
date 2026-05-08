"""Coverage.py 集成服务

负责:

* 在受控环境下执行 pytest + coverage(可选)
* 读取 ``.coverage`` SQLite 数据库,解析覆盖的文件与行号
* 配合 :class:`ASTAnalyzer` 把"覆盖行"还原为"函数签名"
* 解析 *动态上下文*(``coverage --contexts=test``)输出
  ``test_id -> [function_signature, ...]`` 的关联映射,
  作为 Phase 2 静态分析自动建立 TestCaseCodeMapping 的数据来源。

设计原则:

* 不依赖运行时环境必须存在 ``.coverage``;若缺失返回空结果而不是异常
* 使用 ``coverage.CoverageData`` 公共 API,避免直接读 SQLite 内部结构
* 路径规范化:把 coverage 记录的绝对路径转换为相对于仓库根的路径
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from coverage import CoverageData  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - 防御导入
    CoverageData = None  # type: ignore[assignment]

from .ast_analyzer import ASTAnalyzer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileCoverage:
    """单个文件的覆盖详情。"""
    path: str
    covered_lines: tuple[int, ...]
    contexts_by_line: dict[int, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "covered_lines": list(self.covered_lines),
            "contexts_by_line": {k: list(v) for k, v in self.contexts_by_line.items()},
        }


@dataclass(frozen=True)
class CoverageReport:
    """``.coverage`` 数据库的结构化解析结果。"""
    files: tuple[FileCoverage, ...]
    contexts: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "files": [f.to_dict() for f in self.files],
            "contexts": list(self.contexts),
        }


class CoverageService:
    """coverage.py 数据解析与执行封装。"""

    def __init__(
        self,
        repo_path: str | Path,
        coverage_db: str | Path | None = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path does not exist: {repo_path}")
        self.coverage_db = (
            Path(coverage_db).resolve() if coverage_db is not None
            else self.repo_path / ".coverage"
        )
        self._ast = ASTAnalyzer(str(self.repo_path))

    # ------------------------------------------------------------------
    # pytest 执行包装(可选)
    # ------------------------------------------------------------------
    def run_pytest_with_coverage(
        self,
        test_target: str = "tests",
        source: str | None = None,
        with_contexts: bool = True,
        extra_args: list[str] | None = None,
    ) -> tuple[int, str]:
        """在 ``self.repo_path`` 中执行 ``pytest`` 并采集 coverage。

        Returns:
            (returncode, combined stdout/stderr)
        """
        pytest_bin = shutil.which("pytest")
        if pytest_bin is None:
            raise RuntimeError("pytest 未安装或不在 PATH 中,无法采集覆盖率")

        cmd: list[str] = [
            pytest_bin,
            "--cov" + (f"={source}" if source else ""),
            "--cov-report=",  # 不输出 HTML/XML, 只生成 .coverage
        ]
        if with_contexts:
            # coverage 7+: 自动按测试函数划分 context
            cmd.append("--cov-context=test")
        cmd.append(test_target)
        if extra_args:
            cmd.extend(extra_args)

        logger.info("执行 pytest: %s", " ".join(cmd))
        proc = subprocess.run(  # noqa: S603 - 命令来自配置而非用户输入
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    # ------------------------------------------------------------------
    # .coverage 数据库解析
    # ------------------------------------------------------------------
    def parse_coverage_db(self, with_contexts: bool = True) -> CoverageReport:
        """读取 ``.coverage`` 数据库并返回结构化报告。"""
        if CoverageData is None:
            logger.warning("coverage 库未安装,返回空报告")
            return CoverageReport(files=(), contexts=())
        if not self.coverage_db.exists():
            logger.warning("coverage 数据库不存在: %s", self.coverage_db)
            return CoverageReport(files=(), contexts=())

        data = CoverageData(basename=str(self.coverage_db))
        try:
            data.read()
        except Exception as exc:  # pragma: no cover - 数据库损坏
            logger.warning("读取 coverage 数据库失败: %s", exc)
            return CoverageReport(files=(), contexts=())

        contexts: tuple[str, ...] = tuple(
            sorted(c for c in data.measured_contexts() if c)
        )

        files: list[FileCoverage] = []
        for measured in data.measured_files():
            rel_path = self._normalize_path(measured)
            if rel_path is None:
                continue
            covered = tuple(sorted(data.lines(measured) or ()))
            ctx_map: dict[int, tuple[str, ...]] = {}
            if with_contexts:
                try:
                    raw = data.contexts_by_lineno(measured) or {}
                except Exception:  # pragma: no cover - 旧版 coverage 不支持
                    raw = {}
                for line, ctxs in raw.items():
                    ctx_filtered = tuple(c for c in ctxs if c)
                    if ctx_filtered:
                        ctx_map[int(line)] = ctx_filtered
            files.append(FileCoverage(
                path=rel_path,
                covered_lines=covered,
                contexts_by_line=ctx_map,
            ))
        return CoverageReport(files=tuple(files), contexts=contexts)

    # ------------------------------------------------------------------
    # 覆盖率 → 函数签名
    # ------------------------------------------------------------------
    def map_lines_to_functions(
        self, report: CoverageReport | None = None
    ) -> dict[str, set[str]]:
        """将每个文件的覆盖行号映射到函数签名集合。

        Returns:
            ``{file_path: {function_signature, ...}}``
        """
        report = report or self.parse_coverage_db(with_contexts=False)
        result: dict[str, set[str]] = {}
        for file_cov in report.files:
            if not file_cov.path.endswith(".py"):
                continue
            line_to_sig = self._ast.map_lines_to_functions(
                file_cov.path, file_cov.covered_lines
            )
            sigs = set(line_to_sig.values())
            if sigs:
                result[file_cov.path] = sigs
        return result

    def per_test_coverage(
        self, report: CoverageReport | None = None
    ) -> dict[str, set[str]]:
        """解析 *动态上下文*,返回 ``test_id → {function_signature, ...}``。

        ``test_id`` 形如 ``tests/api/test_users.py::test_create_user``,
        与 pytest nodeid 一致,便于映射回 ``TestCase``。
        """
        report = report or self.parse_coverage_db(with_contexts=True)
        per_test: dict[str, set[str]] = {}
        for file_cov in report.files:
            if not file_cov.path.endswith(".py") or not file_cov.contexts_by_line:
                continue
            records = self._ast.parse_file(file_cov.path)
            for line, ctxs in file_cov.contexts_by_line.items():
                signature = _resolve_signature(records, line)
                if signature is None:
                    continue
                for ctx in ctxs:
                    test_id = _strip_context_phase(ctx)
                    per_test.setdefault(test_id, set()).add(signature)
        return per_test

    # ------------------------------------------------------------------
    # Phase 2: 自动建立 TestCaseCodeMapping
    # ------------------------------------------------------------------
    def build_static_mappings(
        self,
        per_test_index: dict[str, set[str]] | None = None,
    ) -> list[dict[str, Any]]:
        """根据 per-test 覆盖率,生成 TestCaseCodeMapping 候选记录。

        每条候选包含:

        * ``test_id``: pytest nodeid
        * ``function_signature``: 形如 ``apps.foo.views:Bar.list``
        * ``confidence``: 静态分析默认 0.8(留 0.2 余量给动态学习覆盖)
        * ``mapping_type``: ``auto_static``

        调用方负责把 ``test_id`` 对应回 Django ``TestCase`` 主键并落库。
        """
        per_test = per_test_index or self.per_test_coverage()
        candidates: list[dict[str, Any]] = []
        for test_id, signatures in per_test.items():
            for sig in signatures:
                candidates.append({
                    "test_id": test_id,
                    "function_signature": sig,
                    "file_path": _signature_to_file(sig),
                    "mapping_type": "auto_static",
                    "confidence": 0.8,
                })
        return candidates

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _normalize_path(self, raw: str) -> str | None:
        """将 coverage 记录的绝对路径转换为相对仓库根的 POSIX 路径。"""
        try:
            p = Path(raw).resolve()
        except OSError:
            return None
        try:
            rel = p.relative_to(self.repo_path)
        except ValueError:
            # coverage 可能记录了仓库外的依赖文件,过滤掉
            return None
        return str(rel).replace("\\", "/")


def _resolve_signature(records: list[Any], line: int) -> str | None:
    for rec in records:
        if rec.covers(line):
            return rec.signature
    return None


def _strip_context_phase(ctx: str) -> str:
    """coverage 7+ 的 context 名形如 ``tests/x.py::test_a|setup``;去掉阶段后缀。"""
    if "|" in ctx:
        return ctx.split("|", 1)[0]
    return ctx


def _signature_to_file(signature: str) -> str:
    """``apps.foo.views:Bar.list`` → ``apps/foo/views.py``。"""
    module = signature.split(":", 1)[0]
    return module.replace(".", "/") + ".py"
