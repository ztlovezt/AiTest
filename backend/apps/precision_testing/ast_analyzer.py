"""Python AST 解析器 — 标准库 ast + astroid

负责将源码中的函数/方法定义提取为节点,并将 diff 行号映射回函数签名。
关键考量:

* 装饰器会让 ``node.lineno`` 指向 ``def`` 行,而装饰器本身位于其上方;
  我们用 ``decorator_list[0].lineno`` 作为函数的真实起始行,避免装饰器
  改动被误判为"非函数变更"。
* DRF ViewSet 的 ``@action`` 装饰器需要单独识别,以便建图时区分常规
  方法与 action 端点。
* AsyncFunctionDef、嵌套类、嵌套函数均需正确归属。
* 子模块导入路径(相对 vs 绝对)统一规范化为 ``apps.module.file:Class.method``。

输出结构:
    [
        {
            "file": "apps/projects/views.py",
            "module": "apps.projects.views",
            "signature": "apps.projects.views:ProjectViewSet.list",
            "name": "list",
            "qualified_name": "ProjectViewSet.list",
            "class_name": "ProjectViewSet",
            "is_async": false,
            "is_action": false,
            "decorators": ["action"],
            "start_line": 15,
            "end_line": 42,
            "body_start_line": 17,
            "lineno_def": 17,
        },
        ...
    ]
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import astroid
except ImportError:  # pragma: no cover - astroid 缺失时降级
    astroid = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FunctionRecord:
    """单个函数/方法的元数据。"""
    file: str
    module: str
    signature: str
    name: str
    qualified_name: str
    class_name: str
    is_async: bool
    is_action: bool
    decorators: tuple[str, ...]
    start_line: int      # 含装饰器的真实起始行
    end_line: int
    body_start_line: int  # `def` 行(decorator 之后第一行)
    lineno_def: int       # 同上(向后兼容字段)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "module": self.module,
            "signature": self.signature,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "class_name": self.class_name,
            "is_async": self.is_async,
            "is_action": self.is_action,
            "decorators": list(self.decorators),
            "start_line": self.start_line,
            "end_line": self.end_line,
            "body_start_line": self.body_start_line,
            "lineno_def": self.lineno_def,
        }

    def covers(self, line: int) -> bool:
        return self.start_line <= line <= self.end_line


@dataclass(frozen=True)
class CallEdge:
    """跨函数调用关系(用于建图)。"""
    caller_signature: str
    callee_name: str
    callee_module: str | None  # 解析失败时为 None
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "caller_signature": self.caller_signature,
            "callee_name": self.callee_name,
            "callee_module": self.callee_module,
            "line": self.line,
        }


class _FunctionCollector(ast.NodeVisitor):
    """递归收集函数定义,正确维护嵌套类/函数的上下文。"""

    def __init__(self, module_dotted: str, file_path: str) -> None:
        self._module = module_dotted
        self._file = file_path
        self._class_stack: list[str] = []
        self.records: list[FunctionRecord] = []

    # ---- class 上下文 ----
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()

    # ---- 普通函数 ----
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect(node, is_async=False)
        # 仍然递归进入,以处理嵌套函数(注意:嵌套函数会单独成为一条记录)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect(node, is_async=True)
        self.generic_visit(node)

    def _collect(self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_async: bool) -> None:
        decorators = _extract_decorator_names(node.decorator_list)
        is_action = any(d in {"action", "list_route", "detail_route"} for d in decorators)
        # 装饰器会出现在 def 之前,start_line 取最早的装饰器行
        if node.decorator_list:
            start_line = min(d.lineno for d in node.decorator_list)
        else:
            start_line = node.lineno
        end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
        body_start_line = node.lineno

        class_name = ".".join(self._class_stack)
        if class_name:
            qualified_name = f"{class_name}.{node.name}"
        else:
            qualified_name = node.name
        signature = f"{self._module}:{qualified_name}"

        self.records.append(FunctionRecord(
            file=self._file,
            module=self._module,
            signature=signature,
            name=node.name,
            qualified_name=qualified_name,
            class_name=class_name,
            is_async=is_async,
            is_action=is_action,
            decorators=tuple(decorators),
            start_line=start_line,
            end_line=end_line,
            body_start_line=body_start_line,
            lineno_def=body_start_line,
        ))


def _extract_decorator_names(decorators: list[ast.expr]) -> list[str]:
    """从装饰器表达式中提取可读的名称(尽量做到 best-effort)。"""
    names: list[str] = []
    for dec in decorators:
        names.append(_decorator_name(dec))
    return names


def _decorator_name(node: ast.expr) -> str:
    """将装饰器节点序列化为字符串名称。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ast.dump(node)


def normalize_module_path(file_path: str) -> str:
    """将 ``apps/projects/views.py`` 规范化为 ``apps.projects.views``。"""
    norm = file_path.replace("\\", "/").strip("./")
    if norm.endswith(".py"):
        norm = norm[:-3]
    if norm.endswith("/__init__"):
        norm = norm[: -len("/__init__")]
    return norm.replace("/", ".")


class ASTAnalyzer:
    """解析 Python 源码,提取函数/类/装饰器信息,并将 diff 行号映射到函数签名。"""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()

    # ------------------------------------------------------------------
    # 主流程: 行号 → 函数签名
    # ------------------------------------------------------------------
    def get_changed_functions(self, diff_result: dict[str, Any]) -> list[dict[str, Any]]:
        """根据 diff 结果,解析出变更的函数列表(JSON 序列化字典)。"""
        records = self.get_changed_function_records(diff_result)
        return [r.to_dict() for r in records]

    def get_changed_function_records(self, diff_result: dict[str, Any]) -> list[FunctionRecord]:
        """同 :py:meth:`get_changed_functions`,但返回结构化对象。"""
        changed_files = diff_result.get("changed_files", [])
        results: list[FunctionRecord] = []
        seen_signatures: set[str] = set()

        for item in changed_files:
            file_path = item.get("path", "")
            if not file_path.endswith(".py"):
                continue
            full_path = self.repo_path / file_path
            if not full_path.exists():
                logger.debug("文件已删除或不存在,跳过: %s", file_path)
                continue
            try:
                source = full_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                logger.warning("读取文件失败 %s: %s", file_path, exc)
                continue

            changed_lines = set(
                item.get("added_lines", []) + item.get("removed_lines", [])
            )
            if not changed_lines:
                continue
            functions = self.parse_source(source, file_path)
            for func in functions:
                if any(func.covers(line) for line in changed_lines):
                    if func.signature in seen_signatures:
                        continue
                    seen_signatures.add(func.signature)
                    results.append(func)
        return results

    # ------------------------------------------------------------------
    # 文件/源码解析
    # ------------------------------------------------------------------
    def parse_file(self, file_path: str) -> list[FunctionRecord]:
        """解析单个文件,返回所有函数定义(供建图全量扫描使用)。"""
        full = self.repo_path / file_path if not Path(file_path).is_absolute() else Path(file_path)
        try:
            source = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("读取文件失败 %s: %s", file_path, exc)
            return []
        rel = str(full.relative_to(self.repo_path)).replace("\\", "/") \
            if full.is_absolute() and full.is_relative_to(self.repo_path) \
            else file_path.replace("\\", "/")
        return self.parse_source(source, rel)

    def parse_source(self, source: str, file_path: str) -> list[FunctionRecord]:
        """解析源码,提取所有函数定义。"""
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            logger.warning("AST 解析失败 %s: %s", file_path, exc)
            return []

        module_dotted = normalize_module_path(file_path)
        collector = _FunctionCollector(module_dotted, file_path.replace("\\", "/"))
        collector.visit(tree)
        return collector.records

    # 兼容 graph_builder 等模块的旧 API
    @staticmethod
    def _extract_functions(source: str, file_path: str) -> list[dict[str, Any]]:
        """旧版 API:返回字典列表(供 graph_builder 等已有调用者复用)。"""
        analyzer = ASTAnalyzer(repo_path=".")
        return [r.to_dict() for r in analyzer.parse_source(source, file_path)]

    # ------------------------------------------------------------------
    # 行号 → 函数签名(单文件)
    # ------------------------------------------------------------------
    def map_lines_to_functions(
        self, file_path: str, lines: Iterable[int]
    ) -> dict[int, str]:
        """将一组行号映射到函数签名。未命中函数的行不会出现在结果中。"""
        records = self.parse_file(file_path)
        line_to_sig: dict[int, str] = {}
        for line in lines:
            for rec in records:
                if rec.covers(line):
                    line_to_sig[line] = rec.signature
                    break
        return line_to_sig

    # ------------------------------------------------------------------
    # 跨模块调用关系(astroid)
    # ------------------------------------------------------------------
    def extract_call_edges(self, file_path: str) -> list[CallEdge]:
        """提取一个文件中所有 caller→callee 调用边(尽力解析跨模块)。

        若 astroid 不可用,则降级为只返回 caller 内的调用 *名字*(callee_module=None)。
        """
        full = self.repo_path / file_path
        if not full.exists():
            return []
        try:
            source = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        records = self.parse_source(source, file_path)
        if not records:
            return []
        # 行号 → caller signature 的快速索引
        line_to_caller: dict[int, str] = {}
        for rec in records:
            for ln in range(rec.body_start_line, rec.end_line + 1):
                line_to_caller[ln] = rec.signature

        edges: list[CallEdge] = []
        if astroid is not None:
            edges.extend(self._extract_calls_astroid(source, file_path, line_to_caller))
        else:
            edges.extend(self._extract_calls_stdlib(source, line_to_caller))
        return edges

    @staticmethod
    def _extract_calls_stdlib(
        source: str, line_to_caller: dict[int, str]
    ) -> list[CallEdge]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        edges: list[CallEdge] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            caller_sig = line_to_caller.get(node.lineno)
            if not caller_sig:
                continue
            name = ASTAnalyzer._call_callable_name(node.func)
            if not name:
                continue
            edges.append(CallEdge(
                caller_signature=caller_sig,
                callee_name=name,
                callee_module=None,
                line=node.lineno,
            ))
        return edges

    @staticmethod
    def _extract_calls_astroid(
        source: str, file_path: str, line_to_caller: dict[int, str]
    ) -> list[CallEdge]:
        """使用 astroid 的 inference 能力解析跨模块调用。"""
        try:
            module = astroid.parse(source, module_name=normalize_module_path(file_path))
        except astroid.AstroidSyntaxError:
            return []

        edges: list[CallEdge] = []
        for node in module.nodes_of_class(astroid.Call):
            caller_sig = line_to_caller.get(node.lineno)
            if not caller_sig:
                continue
            name = ASTAnalyzer._call_callable_name(node.func)
            callee_module: str | None = None
            try:
                inferred = next(node.func.infer(), None)
            except (astroid.InferenceError, StopIteration, RecursionError):
                inferred = None
            if inferred is not None and hasattr(inferred, "root"):
                try:
                    callee_module = inferred.root().name
                except Exception:  # pragma: no cover - astroid 内部异常很多类型
                    callee_module = None
            if name:
                edges.append(CallEdge(
                    caller_signature=caller_sig,
                    callee_name=name,
                    callee_module=callee_module,
                    line=node.lineno,
                ))
        return edges

    @staticmethod
    def _call_callable_name(func_node: Any) -> str:
        """从 ast.Call.func 节点抽取一个可读的"被调用者"名称。"""
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            base = ASTAnalyzer._call_callable_name(func_node.value)
            return f"{base}.{func_node.attr}" if base else func_node.attr
        # astroid 的 Call.func 在某些场景下是 nodes.Name / Attribute,
        # 与 stdlib ast 接口完全兼容,因此沿用同一分支。
        if hasattr(func_node, "as_string"):
            try:
                return func_node.as_string()
            except Exception:  # pragma: no cover
                return ""
        return ""

    # ------------------------------------------------------------------
    # 准确率评估辅助(单元测试可用)
    # ------------------------------------------------------------------
    def function_for_line(self, file_path: str, line: int) -> FunctionRecord | None:
        """单行号查询所属函数(准确率评估的基础工具)。"""
        records = self.parse_file(file_path)
        for rec in records:
            if rec.covers(line):
                return rec
        return None
