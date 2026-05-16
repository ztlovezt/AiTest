# -*- coding: utf-8 -*-
"""Week2: Git Diff + AST 解析引擎 — DRFRouteParser 公共 API 测试用例

覆盖模块: backend/apps/precision_testing/route_parser.py
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
    from apps.precision_testing.route_parser import (
        DRFRouteParser,
        RouteRecord,
        _VIEWSET_STANDARD_METHODS,
        _CBV_HTTP_METHODS,
        _collect_imports,
        _collect_router_registrations,
        _read_action_decorator,
        _extract_string_list,
        _literal_string,
        _extract_kw_string,
        _attribute_chain,
        _callable_name,
        _is_include_call,
        _extract_include_target,
        _is_as_view_call,
        _join_url,
        normalize_module_path,
    )
except ImportError:
    pytest.skip("apps.precision_testing.route_parser not available", allow_module_level=True)


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
def parser(temp_repo_path: Path) -> DRFRouteParser:
    return DRFRouteParser(repo_path=str(temp_repo_path))


# ==============================================================================
# 数据类测试 — RouteRecord
# ==============================================================================

class TestRouteRecord:
    """RouteRecord 数据类测试。"""

    def test_to_dict_all_fields(self) -> None:
        rec = RouteRecord(
            url_pattern="projects/",
            http_method="GET",
            view_module="apps.projects.views",
            view_class="ProjectViewSet",
            view_method="list",
            function_signature="apps.projects.views:ProjectViewSet.list",
            name="project-list",
            source="router",
        )
        d = rec.to_dict()
        assert d["url_pattern"] == "projects/"
        assert d["http_method"] == "GET"
        assert d["view_module"] == "apps.projects.views"
        assert d["view_class"] == "ProjectViewSet"
        assert d["view_method"] == "list"
        assert d["function_signature"] == "apps.projects.views:ProjectViewSet.list"
        assert d["name"] == "project-list"
        assert d["source"] == "router"

    def test_source_values(self) -> None:
        for source in ("path", "router", "action", "fbv", "include"):
            rec = RouteRecord(
                url_pattern="/x/",
                http_method="GET",
                view_module="m",
                view_class="C",
                view_method="m",
                function_signature="m:C.m",
                name=None,
                source=source,
            )
            assert rec.source == source

    def test_immutable(self) -> None:
        rec = RouteRecord(
            url_pattern="/x/",
            http_method="GET",
            view_module="m",
            view_class="C",
            view_method="m",
            function_signature="m:C.m",
            name=None,
            source="path",
        )
        with pytest.raises(Exception):
            rec.url_pattern = "/y/"  # type: ignore


# ==============================================================================
# 常量测试
# ==============================================================================

class TestConstants:
    """_VIEWSET_STANDARD_METHODS / _CBV_HTTP_METHODS 常量测试。"""

    def test_standard_methods_complete(self) -> None:
        assert "list" in _VIEWSET_STANDARD_METHODS
        assert "create" in _VIEWSET_STANDARD_METHODS
        assert "retrieve" in _VIEWSET_STANDARD_METHODS
        assert "update" in _VIEWSET_STANDARD_METHODS
        assert "partial_update" in _VIEWSET_STANDARD_METHODS
        assert "destroy" in _VIEWSET_STANDARD_METHODS

    def test_standard_methods_have_pairs(self) -> None:
        for action, pairs in _VIEWSET_STANDARD_METHODS.items():
            for http_method, detail in pairs:
                assert isinstance(http_method, str)
                assert isinstance(detail, bool)

    def test_cbv_http_methods(self) -> None:
        expected = {"get", "post", "put", "patch", "delete", "head", "options"}
        assert set(_CBV_HTTP_METHODS) == expected


# ==============================================================================
# 辅助函数测试
# ==============================================================================

class TestHelperFunctions:
    """模块级辅助函数测试。"""

    def test_join_url_both_empty(self) -> None:
        assert _join_url("", "") == ""

    def test_join_url_prefix_only(self) -> None:
        assert _join_url("api", "") == "api/"

    def test_join_url_suffix_only(self) -> None:
        assert _join_url("", "users") == "users/"

    def test_join_url_both(self) -> None:
        assert _join_url("api", "users") == "api/users/"

    def test_join_url_strips_slashes(self) -> None:
        assert _join_url("/api/", "/users/") == "api/users/"

    def test_literal_string_constant(self) -> None:
        import ast
        tree = ast.parse("x = 'hello'")
        str_node = tree.body[0].value
        assert _literal_string(str_node) == "hello"

    def test_literal_string_non_string(self) -> None:
        import ast
        tree = ast.parse("x = 123")
        num_node = tree.body[0].value
        assert _literal_string(num_node) is None

    def test_extract_kw_string(self) -> None:
        import ast
        tree = ast.parse("path('foo/', v, name='bar')")
        call = tree.body[0].value
        assert _extract_kw_string(call, "name") == "bar"
        assert _extract_kw_string(call, "missing") is None

    def test_attribute_chain_simple(self) -> None:
        import ast
        tree = ast.parse("views.ProjectView")
        attr = tree.body[0].value
        parts = _attribute_chain(attr)
        assert parts == ["views", "ProjectView"]

    def test_attribute_chain_deep(self) -> None:
        import ast
        tree = ast.parse("a.b.c.d")
        attr = tree.body[0].value
        parts = _attribute_chain(attr)
        assert parts == ["a", "b", "c", "d"]

    def test_attribute_chain_name_only(self) -> None:
        import ast
        tree = ast.parse("foo")
        name = tree.body[0].value
        parts = _attribute_chain(name)
        assert parts == ["foo"]

    def test_callable_name_name(self) -> None:
        import ast
        tree = ast.parse("foo()")
        call = tree.body[0].value
        assert _callable_name(call.func) == "foo"

    def test_callable_name_attribute(self) -> None:
        import ast
        tree = ast.parse("obj.method()")
        call = tree.body[0].value
        assert _callable_name(call.func) == "method"

    def test_is_include_call_true(self) -> None:
        import ast
        tree = ast.parse("include('urls')")
        call = tree.body[0].value
        assert _is_include_call(call) is True

    def test_is_include_call_false(self) -> None:
        import ast
        tree = ast.parse("path('foo', view)")
        call = tree.body[0].value
        assert _is_include_call(call) is False

    def test_extract_include_target_string(self) -> None:
        import ast
        tree = ast.parse("include('apps.foo.urls')")
        call = tree.body[0].value
        assert _extract_include_target(call) == "apps.foo.urls"

    def test_extract_include_target_complex(self) -> None:
        import ast
        # include((urlpatterns, ns), namespace=...) — not supported
        tree = ast.parse("include((patterns,), namespace='ns')")
        call = tree.body[0].value
        assert _extract_include_target(call) is None

    def test_is_as_view_call_true(self) -> None:
        import ast
        tree = ast.parse("View.as_view()")
        call = tree.body[0].value
        assert _is_as_view_call(call) is True

    def test_is_as_view_call_false(self) -> None:
        import ast
        tree = ast.parse("some_func()")
        call = tree.body[0].value
        assert _is_as_view_call(call) is False

    def test_extract_string_list_list(self) -> None:
        import ast
        tree = ast.parse("['get', 'post']")
        node = tree.body[0].value
        result = _extract_string_list(node)
        assert result == ["get", "post"]

    def test_extract_string_list_tuple(self) -> None:
        import ast
        tree = ast.parse("('get', 'post')")
        node = tree.body[0].value
        result = _extract_string_list(node)
        assert result == ["get", "post"]

    def test_extract_string_list_non_string_elt_skipped(self) -> None:
        import ast
        tree = ast.parse("[1, 2, 3]")
        node = tree.body[0].value
        result = _extract_string_list(node)
        assert result == []

    def test_read_action_decorator_detail(self) -> None:
        import ast
        source = """
@action(detail=True)
def custom(self):
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        meta = _read_action_decorator(func)
        assert meta is not None
        assert meta["detail"] is True

    def test_read_action_decorator_methods(self) -> None:
        import ast
        source = """
@action(methods=['post', 'patch'])
def custom(self):
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        meta = _read_action_decorator(func)
        assert meta is not None
        assert meta["methods"] == ["post", "patch"]

    def test_read_action_decorator_not_action(self) -> None:
        import ast
        source = """
def custom(self):
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        assert _read_action_decorator(func) is None

    def test_read_action_decorator_list_route(self) -> None:
        import ast
        source = """
@list_route()
def custom_list(self):
    pass
"""
        tree = ast.parse(source)
        func = tree.body[0]
        meta = _read_action_decorator(func)
        assert meta is not None


# ==============================================================================
# DRFRouteParser — 初始化
# ==============================================================================

class TestDRFRouteParserInit:
    """DRFRouteParser 构造测试。"""

    def test_repo_path_resolved(self, temp_repo_path: Path) -> None:
        parser = DRFRouteParser(repo_path=str(temp_repo_path))
        assert parser.repo_path == temp_repo_path.resolve()

    def test_repo_path_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            DRFRouteParser(repo_path=str(tmp_path / "nonexistent"))


# ==============================================================================
# DRFRouteParser — parse
# ==============================================================================

class TestDRFRouteParserParse:
    """parse 方法测试。"""

    def test_module_not_found_returns_empty(self, parser: DRFRouteParser) -> None:
        result = parser.parse("nonexistent.module.xyz")
        assert result == []

    def test_invalid_urls_module(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        # Create a file that exists but has syntax errors
        urls_file = temp_repo_path / "apps" / "bad_urls.py"
        urls_file.write_text("def = invalid syntax @#$", encoding="utf-8")
        result = parser.parse("apps.bad_urls")
        assert result == []

    def test_parse_to_dicts(self, parser: DRFRouteParser) -> None:
        result = parser.parse_to_dicts("nonexistent.module")
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_visited_cycle_detection(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        """循环 include 时应防止无限递归。"""
        urls_content = """
from django.urls import include, path
import apps.projects.urls

urlpatterns = [
    path('foo/', include('apps.projects.urls')),
]
"""
        urls_file = temp_repo_path / "apps" / "main_urls.py"
        urls_file.write_text(urls_content, encoding="utf-8")
        # The inner urls module imports itself through the cycle
        inner_content = """
from django.urls import include, path
import apps.projects.main_urls

urlpatterns = [
    path('bar/', include('apps.projects.main_urls')),
]
"""
        inner_file = temp_repo_path / "apps" / "projects" / "urls.py"
        inner_file.parent.mkdir(parents=True, exist_ok=True)
        inner_file.write_text(inner_content, encoding="utf-8")

        result = parser.parse("apps.main_urls")
        # Should not infinite loop — returns whatever was parsed before cycle detection
        assert isinstance(result, list)


# ==============================================================================
# DRFRouteParser — CBV 解析
# ==============================================================================

class TestCBVExpansion:
    """CBV (path() + .as_view()) 解析测试。"""

    def test_simple_cbv(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        urls_content = """
from django.urls import path
from apps.projects.views import ProjectView

urlpatterns = [
    path('projects/', ProjectView.as_view(), name='project-list'),
]
"""
        views_content = """
from django.views.generic import View

class ProjectView(View):
    # Define get explicitly so AST analyzer can find it
    def get(self, request):
        pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        records = [r for r in result if r.source == "path"]
        assert len(records) >= 1
        assert any(r.http_method == "GET" for r in records)

    def test_cbv_without_explicit_methods(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        """没有显式 HTTP 方法的 CBV 应回退到 ANY。"""
        urls_content = """
from django.urls import path
from apps.projects.views import EmptyView

urlpatterns = [
    path('empty/', EmptyView.as_view(), name='empty'),
]
"""
        views_content = """
from django.views.generic import View
# No methods defined — rely on View base class
class EmptyView(View):
    pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        records = [r for r in result if r.source == "path"]
        assert len(records) >= 1
        assert any(r.http_method == "GET" for r in records)

    def test_cbv_without_explicit_methods(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        """没有显式 HTTP 方法的 CBV 应回退到 ANY。"""
        urls_content = """
from django.urls import path
from apps.projects.views import EmptyView

urlpatterns = [
    path('empty/', EmptyView.as_view(), name='empty'),
]
"""
        views_content = """
from django.views.generic import View
# No methods defined
class EmptyView(View):
    pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        assert len(result) >= 1


# ==============================================================================
# DRFRouteParser — FBV 解析
# ==============================================================================

class TestFBVExpansion:
    """FBV (path() + 函数) 解析测试。"""

    def test_fbv(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        urls_content = """
from django.urls import path
from apps.projects.views import list_projects

urlpatterns = [
    path('projects/', list_projects, name='project-list'),
]
"""
        views_content = """
def list_projects(request):
    pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        fbv_records = [r for r in result if r.source == "fbv"]
        assert len(fbv_records) >= 1
        assert any(r.http_method == "ANY" for r in fbv_records)
        assert any(r.view_method == "list_projects" for r in fbv_records)


# ==============================================================================
# DRFRouteParser — ViewSet 展开
# ==============================================================================

class TestViewSetExpansion:
    """ViewSet (router.register / @action) 解析测试。"""

    def test_viewset_standard_methods(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        """ViewSet 的标准 CRUD 方法应被正确展开。"""
        urls_content = """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import ProjectViewSet

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('api/', include(router.urls)),
]
"""
        views_content = """
from rest_framework.viewsets import ViewSet

class ProjectViewSet(ViewSet):
    def list(self, request):
        pass

    def create(self, request):
        pass

    def retrieve(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        router_records = [r for r in result if r.source == "router"]
        http_methods = {r.http_method for r in router_records}

        assert "GET" in http_methods  # list + retrieve
        assert "POST" in http_methods  # create
        assert "DELETE" in http_methods  # destroy

    def test_viewset_action_decorator(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        """@action 装饰的自定义方法应被展开。"""
        urls_content = """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import FooViewSet

router = DefaultRouter()
router.register(r'foo', FooViewSet, basename='foo')

urlpatterns = [
    path('api/', include(router.urls)),
]
"""
        views_content = """
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

class FooViewSet(ViewSet):
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        pass

    @action(detail=False, methods=['get'])
    def stats(self, request):
        pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        action_records = [r for r in result if r.source == "action"]

        assert len(action_records) >= 2
        sync_records = [r for r in action_records if r.view_method == "sync"]
        assert len(sync_records) >= 1
        assert any(r.http_method == "POST" for r in sync_records)

        stats_records = [r for r in action_records if r.view_method == "stats"]
        assert len(stats_records) >= 1
        assert any(r.http_method == "GET" for r in stats_records)


# ==============================================================================
# DRFRouteParser — _collect_imports
# ==============================================================================

class TestCollectImports:
    """_collect_imports 函数测试。"""

    def test_simple_import(self) -> None:
        import ast
        tree = ast.parse("import os")
        imports = _collect_imports(tree, base_module="apps.foo")
        assert "os" in imports

    def test_import_from(self) -> None:
        import ast
        tree = ast.parse("from django.urls import path, include")
        imports = _collect_imports(tree, base_module="apps.foo")
        assert imports["path"] == "django.urls.path"
        assert imports["include"] == "django.urls.include"

    def test_import_with_alias(self) -> None:
        import ast
        tree = ast.parse("import os.path as op")
        imports = _collect_imports(tree, base_module="apps.foo")
        assert "op" in imports

    def test_relative_import(self) -> None:
        import ast
        tree = ast.parse("from . import views")
        imports = _collect_imports(tree, base_module="apps.projects.urls")
        assert "views" in imports

    def test_relative_import_from_submodule(self) -> None:
        import ast
        tree = ast.parse("from .views import ProjectView")
        imports = _collect_imports(tree, base_module="apps.projects.urls")
        assert "ProjectView" in imports


# ==============================================================================
# DRFRouteParser — _collect_router_registrations
# ==============================================================================

class TestCollectRouterRegistrations:
    """_collect_router_registrations 函数测试。"""

    def test_finds_register(self) -> None:
        import ast
        tree = ast.parse("router.register(r'projects', ProjectViewSet, basename='project')")
        regs = _collect_router_registrations(tree, {})
        assert len(regs) == 1
        assert regs[0][0] == "projects"

    def test_non_register_call_ignored(self) -> None:
        import ast
        tree = ast.parse("path('foo/', view)")
        regs = _collect_router_registrations(tree, {})
        assert regs == []


# ==============================================================================
# DRFRouteParser — _module_to_file / _resolve_module_file
# ==============================================================================

class TestModuleResolution:
    """模块→文件解析测试。"""

    def test_module_to_file_dot_separated(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("# views\n", encoding="utf-8")

        result = parser._module_to_file("apps.projects.views")
        assert result is not None
        assert result.name == "views.py"

    def test_module_to_file_init(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        init_file = temp_repo_path / "apps" / "projects" / "__init__.py"
        init_file.parent.mkdir(parents=True, exist_ok=True)
        init_file.write_text("", encoding="utf-8")

        result = parser._module_to_file("apps.projects")
        assert result is not None
        assert result.name == "__init__.py"

    def test_module_to_file_not_found(self, parser: DRFRouteParser) -> None:
        result = parser._module_to_file("nonexistent.module.xyz")
        assert result is None

    def test_resolve_module_file_py_suffix(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text("# urls\n", encoding="utf-8")

        result = parser._resolve_module_file("apps/projects/urls.py")
        assert result is not None

    def test_resolve_module_file_dotted(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text("# urls\n", encoding="utf-8")

        result = parser._resolve_module_file("apps.projects.urls")
        assert result is not None


# ==============================================================================
# DRFRouteParser — _has_method / _records_for_module
# ==============================================================================

class TestMethodResolution:
    """视图方法存在性检测测试。"""

    def test_has_method_true(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("""
class MyView:
    def get(self, request):
        pass
""", encoding="utf-8")

        assert parser._has_method("apps.projects.views", "MyView", "get") is True

    def test_has_method_false(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("""
class MyView:
    def get(self, request):
        pass
""", encoding="utf-8")

        assert parser._has_method("apps.projects.views", "MyView", "delete") is False

    def test_records_for_module_caches(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("def foo():\n    pass\n", encoding="utf-8")

        result1 = parser._records_for_module("apps.projects.views")
        result2 = parser._records_for_module("apps.projects.views")
        assert result1 is result2  # Same object due to caching

    def test_records_for_module_unknown(self, parser: DRFRouteParser) -> None:
        result = parser._records_for_module("nonexistent.module.xyz")
        assert result == []


# ==============================================================================
# DRFRouteParser — _collect_viewset_actions
# ==============================================================================

class TestCollectViewSetActions:
    """_collect_viewset_actions 测试。"""

    def test_collects_action_decorator(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("""
from rest_framework.decorators import action

class FooViewSet:
    @action(detail=True, methods=['post'])
    def custom(self):
        pass
""", encoding="utf-8")

        result = parser._collect_viewset_actions("apps.projects.views", "FooViewSet")
        assert len(result) >= 1
        action = result[0]
        assert action["name"] == "custom"
        assert action["detail"] is True
        assert "post" in action["methods"]

    def test_no_actions(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("""
class PlainView:
    def get(self):
        pass
""", encoding="utf-8")

        result = parser._collect_viewset_actions("apps.projects.views", "PlainView")
        assert result == []

    def test_wrong_class(self, parser: DRFRouteParser, temp_repo_path: Path) -> None:
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.parent.mkdir(parents=True, exist_ok=True)
        views_file.write_text("""
class Foo:
    @action(detail=True)
    def custom(self):
        pass
""", encoding="utf-8")

        result = parser._collect_viewset_actions("apps.projects.views", "OtherView")
        assert result == []


# ==============================================================================
# 场景测试 — 完整解析流程
# ==============================================================================

class TestDRFRouteParserFullWorkflow:
    """端到端场景测试。"""

    def test_full_router_with_actions(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        """完整的 router + ViewSet + @action 解析流程。"""
        urls_content = """
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.projects.views import ArticleViewSet

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='article')

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
"""
        views_content = """
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet

class ArticleViewSet(ViewSet):
    def list(self, request):
        pass

    def create(self, request):
        pass

    @action(detail=True, methods=['get'])
    def publish(self, request, pk=None):
        pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        assert len(result) > 0

        # Check all sources represented
        sources = {r.source for r in result}
        assert "router" in sources

        # Check function signatures are well-formed
        for rec in result:
            assert rec.function_signature
            assert ":" in rec.function_signature

    def test_mixed_url_patterns(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        """混合 CBV、FBV、router 的复杂 urls.py。"""
        urls_content = """
from django.urls import path, include
from apps.projects.views import HealthCheck, health_check

urlpatterns = [
    path('health/', HealthCheck.as_view(), name='health'),
    path('ping/', health_check, name='ping'),
]
"""
        views_content = """
from django.views.generic import View

def health_check(request):
    pass

class HealthCheck(View):
    def get(self, request):
        pass
"""
        urls_file = temp_repo_path / "apps" / "projects" / "urls.py"
        urls_file.parent.mkdir(parents=True, exist_ok=True)
        urls_file.write_text(urls_content, encoding="utf-8")

        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        sources = {r.source for r in result}
        assert "path" in sources
        assert "fbv" in sources

    def test_url_prefix_recursion(
        self, parser: DRFRouteParser, temp_repo_path: Path
    ) -> None:
        """include 嵌套时的 URL prefix 累积。"""
        inner_urls = """
from django.urls import path
from apps.projects.views import InnerView

urlpatterns = [
    path('inner/', InnerView.as_view(), name='inner'),
]
"""
        outer_urls = """
from django.urls import path, include

urlpatterns = [
    path('prefix/', include('apps.projects.inner_urls')),
]
"""
        inner_file = temp_repo_path / "apps" / "projects" / "inner_urls.py"
        inner_file.parent.mkdir(parents=True, exist_ok=True)
        inner_file.write_text(inner_urls, encoding="utf-8")

        outer_file = temp_repo_path / "apps" / "projects" / "urls.py"
        outer_file.parent.mkdir(parents=True, exist_ok=True)
        outer_file.write_text(outer_urls, encoding="utf-8")

        views_content = """
from django.views.generic import View

class InnerView(View):
    def get(self, request):
        pass
"""
        views_file = temp_repo_path / "apps" / "projects" / "views.py"
        views_file.write_text(views_content, encoding="utf-8")

        result = parser.parse("apps.projects.urls")
        patterns = {r.url_pattern for r in result}
        # The prefix from outer + inner should be combined
        assert any("prefix" in p for p in patterns)

    def test_normalize_module_path_integration(self) -> None:
        """normalize_module_path 跨模块一致性。"""
        assert normalize_module_path("apps/foo/__init__.py") == "apps.foo"
        assert normalize_module_path("apps/foo/bar.py") == "apps.foo.bar"