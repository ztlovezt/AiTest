"""DRF / Django URLConf 静态解析器

把 ``urls.py`` 中的路由声明静态解析为
``URL pattern → ViewSet method`` 的结构化记录。

支持的语法形态:

* ``path('foo/', SomeView.as_view(), name='...')`` — CBV
* ``path('foo/', some_function_view, name='...')`` — FBV
* ``path('', include('apps.foo.urls'))`` — 递归子模块
* ``DefaultRouter().register(r'foo', FooViewSet, basename='foo')`` — 路由注册器
* ``@action`` 装饰的 ViewSet 自定义动作

该解析器**完全不执行用户代码**(纯 AST),因此适合在 CI/沙箱环境运行。
"""
from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .ast_analyzer import ASTAnalyzer, normalize_module_path

logger = logging.getLogger(__name__)


# DRF DefaultRouter / SimpleRouter 的 ViewSet 标准方法映射
_VIEWSET_STANDARD_METHODS: dict[str, list[tuple[str, bool]]] = {
    # action_name: [(http_method, detail), ...]
    "list":           [("GET", False)],
    "create":         [("POST", False)],
    "retrieve":       [("GET", True)],
    "update":         [("PUT", True)],
    "partial_update": [("PATCH", True)],
    "destroy":        [("DELETE", True)],
}

# Django CBV/APIView 的常见 HTTP 方法处理器
_CBV_HTTP_METHODS: tuple[str, ...] = (
    "get", "post", "put", "patch", "delete", "head", "options",
)


@dataclass(frozen=True)
class RouteRecord:
    """单条 URL 路由 → 视图方法映射记录。"""
    url_pattern: str
    http_method: str
    view_module: str
    view_class: str
    view_method: str
    function_signature: str
    name: str | None
    source: str  # 'path' | 'router' | 'action' | 'fbv' | 'include'

    def to_dict(self) -> dict[str, Any]:
        return {
            "url_pattern": self.url_pattern,
            "http_method": self.http_method,
            "view_module": self.view_module,
            "view_class": self.view_class,
            "view_method": self.view_method,
            "function_signature": self.function_signature,
            "name": self.name,
            "source": self.source,
        }


class DRFRouteParser:
    """解析 Django/DRF urls.py,输出 URL → ViewSet.method 映射。"""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repo path does not exist: {repo_path}")
        self._ast_analyzer = ASTAnalyzer(str(self.repo_path))
        # 缓存:已解析过的 module → 函数记录
        self._module_cache: dict[str, list[Any]] = {}

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------
    def parse(
        self,
        urls_module: str,
        url_prefix: str = "",
        _visited: set[str] | None = None,
    ) -> list[RouteRecord]:
        """解析一个 urls.py 模块,递归展开 include。

        Args:
            urls_module: 形如 ``apps.projects.urls`` 的点分模块路径,
                也可以是相对仓库根的文件路径(如 ``apps/projects/urls.py``)。
            url_prefix: 父级 URL 前缀(递归时使用)。
            _visited: 防御循环 include 的访问集合。
        """
        _visited = _visited or set()
        if urls_module in _visited:
            return []
        _visited.add(urls_module)

        file_path = self._resolve_module_file(urls_module)
        if file_path is None:
            logger.debug("无法定位 urls 模块: %s", urls_module)
            return []
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("读取 urls 文件失败 %s: %s", file_path, exc)
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            logger.warning("AST 解析 urls 失败 %s: %s", file_path, exc)
            return []

        imports = _collect_imports(tree, base_module=normalize_module_path(
            str(file_path.relative_to(self.repo_path)).replace("\\", "/")
        ))
        router_registrations = _collect_router_registrations(tree, imports)

        records: list[RouteRecord] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func_name = _callable_name(node.func)
            if func_name in {"path", "re_path"}:
                records.extend(self._parse_path_call(node, imports, url_prefix, _visited))
        # router.register(...) 展开
        for prefix, view_class_ref in router_registrations:
            view_class_module, view_class = self._resolve_view_reference(view_class_ref, imports)
            if not view_class:
                continue
            full_prefix = _join_url(url_prefix, prefix)
            records.extend(self._expand_viewset(
                full_prefix, view_class_module, view_class
            ))
        return records

    def parse_to_dicts(self, urls_module: str, url_prefix: str = "") -> list[dict[str, Any]]:
        """同 :py:meth:`parse`,返回 JSON 可序列化字典。"""
        return [r.to_dict() for r in self.parse(urls_module, url_prefix)]

    # ------------------------------------------------------------------
    # path() / include() 解析
    # ------------------------------------------------------------------
    def _parse_path_call(
        self,
        call: ast.Call,
        imports: dict[str, str],
        url_prefix: str,
        visited: set[str],
    ) -> list[RouteRecord]:
        if len(call.args) < 2:
            return []
        url_pattern = _literal_string(call.args[0])
        if url_pattern is None:
            return []
        view_arg = call.args[1]
        name = _extract_kw_string(call, "name")
        full_url = _join_url(url_prefix, url_pattern)

        # include('apps.foo.urls') / include(other_module.urlpatterns, ...)
        if _is_include_call(view_arg):
            inner = _extract_include_target(view_arg)
            if inner:
                return self.parse(inner, url_prefix=full_url, _visited=visited)
            return []

        # CBV: SomeView.as_view()
        if _is_as_view_call(view_arg):
            view_class_ref = _attribute_chain(view_arg.func.value)  # type: ignore[union-attr]
            module, view_class = self._resolve_view_reference(view_class_ref, imports)
            if not view_class:
                return []
            return self._expand_cbv(full_url, module, view_class, name=name)

        # FBV: 直接传函数
        if isinstance(view_arg, (ast.Name, ast.Attribute)):
            view_ref = _attribute_chain(view_arg)
            module, callable_name = self._resolve_view_reference(view_ref, imports)
            if not callable_name:
                return []
            signature = f"{module}:{callable_name}"
            return [RouteRecord(
                url_pattern=full_url,
                http_method="ANY",
                view_module=module,
                view_class="",
                view_method=callable_name,
                function_signature=signature,
                name=name,
                source="fbv",
            )]
        return []

    # ------------------------------------------------------------------
    # ViewSet / CBV 展开
    # ------------------------------------------------------------------
    def _expand_viewset(
        self, url_prefix: str, view_module: str, view_class: str
    ) -> list[RouteRecord]:
        """根据 DefaultRouter 规则展开 ViewSet 的标准 URL + @action 自定义动作。"""
        records: list[RouteRecord] = []
        # 标准 CRUD
        for action_name, http_pairs in _VIEWSET_STANDARD_METHODS.items():
            if not self._has_method(view_module, view_class, action_name):
                continue
            for http, detail in http_pairs:
                url = _join_url(url_prefix, "{pk}/" if detail else "")
                signature = f"{view_module}:{view_class}.{action_name}"
                records.append(RouteRecord(
                    url_pattern=url,
                    http_method=http,
                    view_module=view_module,
                    view_class=view_class,
                    view_method=action_name,
                    function_signature=signature,
                    name=f"{view_class}-{action_name}",
                    source="router",
                ))
        # @action 装饰器
        for action_record in self._collect_viewset_actions(view_module, view_class):
            method_name = action_record["name"]
            detail = action_record.get("detail", False)
            http_methods: list[str] = action_record.get("methods") or ["GET"]
            for http in http_methods:
                url = _join_url(
                    url_prefix,
                    f"{{pk}}/{method_name}/" if detail else f"{method_name}/",
                )
                signature = f"{view_module}:{view_class}.{method_name}"
                records.append(RouteRecord(
                    url_pattern=url,
                    http_method=http.upper(),
                    view_module=view_module,
                    view_class=view_class,
                    view_method=method_name,
                    function_signature=signature,
                    name=f"{view_class}-{method_name}",
                    source="action",
                ))
        return records

    def _expand_cbv(
        self, url: str, view_module: str, view_class: str, *, name: str | None
    ) -> list[RouteRecord]:
        """CBV(APIView 或 ListCreateAPIView 等):导出已实现的 HTTP 方法。"""
        records: list[RouteRecord] = []
        for method_name in _CBV_HTTP_METHODS:
            if not self._has_method(view_module, view_class, method_name):
                continue
            signature = f"{view_module}:{view_class}.{method_name}"
            records.append(RouteRecord(
                url_pattern=url,
                http_method=method_name.upper(),
                view_module=view_module,
                view_class=view_class,
                view_method=method_name,
                function_signature=signature,
                name=name,
                source="path",
            ))
        if not records:
            # 兜底:即使没找到 HTTP 处理方法,也保留一条 ANY 记录
            signature = f"{view_module}:{view_class}"
            records.append(RouteRecord(
                url_pattern=url,
                http_method="ANY",
                view_module=view_module,
                view_class=view_class,
                view_method="",
                function_signature=signature,
                name=name,
                source="path",
            ))
        return records

    # ------------------------------------------------------------------
    # 视图模块定位与方法查询
    # ------------------------------------------------------------------
    def _resolve_view_reference(
        self,
        ref: list[str] | None,
        imports: dict[str, str],
    ) -> tuple[str, str]:
        """把 ``views.ProjectView`` 这样的引用解析为 (module, class_name)。

        对于 ``from apps.projects.views import ProjectView`` 这类直接导入,
        imports["ProjectView"] == "apps.projects.views.ProjectView",
        此时 class_name 是最后一段, module 是去掉最后一段的剩余部分。
        """
        if not ref:
            return "", ""
        head, *rest = ref
        if head in imports:
            full = imports[head]
            if rest:
                # ref = ['views', 'ProjectView'], full = 'apps.projects.views'
                return full, rest[0]
            # ref = ['ProjectView'], full = 'apps.projects.views.ProjectView'
            # 去掉最后一节得到 module
            parts = full.rsplit(".", 1)
            return parts[0], parts[1] if len(parts) > 1 else head
        # 没找到 import,尽量推断
        if rest:
            return head, rest[0]
        return "", head

    def _has_method(self, module: str, class_name: str, method: str) -> bool:
        for rec in self._records_for_module(module):
            if rec.class_name == class_name and rec.name == method:
                return True
        return False

    def _collect_viewset_actions(
        self, module: str, class_name: str
    ) -> list[dict[str, Any]]:
        """收集 ViewSet 上 @action 装饰器的方法(含 detail / methods 参数)。"""
        results: list[dict[str, Any]] = []
        file_path = self._module_to_file(module)
        if file_path is None:
            return results
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            return results

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            for child in node.body:
                if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                action_meta = _read_action_decorator(child)
                if action_meta is None:
                    continue
                results.append({
                    "name": child.name,
                    "detail": action_meta.get("detail", False),
                    "methods": action_meta.get("methods"),
                })
        return results

    def _records_for_module(self, module: str) -> list[Any]:
        if module in self._module_cache:
            return self._module_cache[module]
        file_path = self._module_to_file(module)
        if file_path is None:
            self._module_cache[module] = []
            return []
        rel = str(file_path.relative_to(self.repo_path)).replace("\\", "/")
        records = self._ast_analyzer.parse_file(rel)
        self._module_cache[module] = records
        return records

    def _module_to_file(self, module: str) -> Path | None:
        if not module:
            return None
        candidate = self.repo_path / (module.replace(".", "/") + ".py")
        if candidate.exists():
            return candidate
        candidate_pkg = self.repo_path / (module.replace(".", "/")) / "__init__.py"
        if candidate_pkg.exists():
            return candidate_pkg
        return None

    def _resolve_module_file(self, urls_module: str) -> Path | None:
        # 既支持 'apps.foo.urls' 也支持 'apps/foo/urls.py'
        if urls_module.endswith(".py"):
            p = self.repo_path / urls_module
            return p if p.exists() else None
        return self._module_to_file(urls_module)


# ===================================================================
# 模块级辅助
# ===================================================================
def _collect_imports(tree: ast.AST, *, base_module: str) -> dict[str, str]:
    """采集 import 语句,返回 ``alias_or_name → fully_qualified_module`` 映射。"""
    imports: dict[str, str] = {}
    base_pkg = base_module.rsplit(".", 1)[0] if "." in base_module else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            if level > 0:
                # 相对导入: from . import views / from .views import X
                parts = base_pkg.split(".") if base_pkg else []
                # 上溯 level 层
                trim = max(0, len(parts) - (level - 1))
                resolved_pkg = ".".join(parts[:trim])
                resolved = (
                    f"{resolved_pkg}.{module}" if module and resolved_pkg
                    else module or resolved_pkg
                )
            else:
                resolved = module
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                imports[local_name] = (
                    f"{resolved}.{alias.name}" if resolved else alias.name
                )
                # 同时把"模块名"形式记下来,方便 views.SomeView 引用
                if resolved and not alias.asname:
                    imports.setdefault(alias.name, f"{resolved}.{alias.name}")
                if resolved:
                    imports.setdefault(resolved.split(".")[-1], resolved)
    return imports


def _collect_router_registrations(
    tree: ast.AST, imports: dict[str, str]
) -> list[tuple[str, list[str]]]:
    """采集 ``router.register(prefix, ViewSet, ...)`` 调用。

    Returns:
        ``[(prefix, ViewSet 引用链), ...]``
    """
    registrations: list[tuple[str, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "register":
            continue
        if len(node.args) < 2:
            continue
        prefix = _literal_string(node.args[0])
        if prefix is None:
            continue
        view_ref = _attribute_chain(node.args[1])
        if not view_ref:
            continue
        registrations.append((prefix, view_ref))
    return registrations


def _read_action_decorator(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any] | None:
    """从函数装饰器中读取 ``@action(detail=..., methods=[...])`` 配置。"""
    for dec in func.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        name = _callable_name(dec.func)
        if name not in {"action", "list_route", "detail_route"}:
            continue
        meta: dict[str, Any] = {}
        for kw in dec.keywords:
            if kw.arg == "detail" and isinstance(kw.value, ast.Constant):
                meta["detail"] = bool(kw.value.value)
            elif kw.arg == "methods":
                meta["methods"] = _extract_string_list(kw.value)
        return meta
    return None


def _extract_string_list(node: ast.expr) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [
            elt.value for elt in node.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def _literal_string(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_kw_string(call: ast.Call, key: str) -> str | None:
    for kw in call.keywords:
        if kw.arg == key:
            return _literal_string(kw.value)
    return None


def _attribute_chain(node: ast.expr) -> list[str]:
    """``views.ProjectViewSet`` → ``['views', 'ProjectViewSet']``。"""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.insert(0, node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.insert(0, node.id)
        return parts
    return []


def _callable_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _is_include_call(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and _callable_name(node.func) == "include"


def _extract_include_target(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    # include((urlpatterns, app_namespace), namespace=...) — 当前不展开
    return None


def _is_as_view_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "as_view"
    )


def _join_url(prefix: str, suffix: str) -> str:
    p = prefix.strip("/")
    s = suffix.strip("/")
    if not p:
        return f"{s}/" if s else ""
    if not s:
        return f"{p}/"
    return f"{p}/{s}/"
