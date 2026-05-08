"""DRFRouteParser 单元测试。

覆盖目标:
    * ``path('foo/', SomeView.as_view())`` 解析为 CBV 多 HTTP 方法
    * ``path('foo/', some_function_view)`` FBV
    * ``router.register(r'projects', ProjectViewSet)`` ViewSet 标准动作
    * ``@action`` 装饰器 → 自定义动作 URL
    * ``include('apps.foo.urls')`` 递归
    * 递归 include 防御
    * 模块级辅助函数行为
"""
from __future__ import annotations

import textwrap

import pytest

from apps.precision_testing.route_parser import (
    DRFRouteParser,
    RouteRecord,
    _attribute_chain,
    _callable_name,
    _is_as_view_call,
    _is_include_call,
    _join_url,
    _literal_string,
)
import ast


# ----------------------------------------------------------------------
# 模块级辅助
# ----------------------------------------------------------------------
class TestUrlJoin:
    @pytest.mark.parametrize("prefix,suffix,expected", [
        ("", "", ""),
        ("api/v1", "", "api/v1/"),
        ("", "users", "users/"),
        ("api/v1", "users", "api/v1/users/"),
        ("/api/v1/", "/users/", "api/v1/users/"),
    ])
    def test_join(self, prefix: str, suffix: str, expected: str) -> None:
        assert _join_url(prefix, suffix) == expected


class TestAstHelpers:
    def test_literal_string(self) -> None:
        node = ast.parse("'hello'").body[0].value
        assert _literal_string(node) == "hello"
        node2 = ast.parse("123").body[0].value
        assert _literal_string(node2) is None

    def test_attribute_chain(self) -> None:
        tree = ast.parse("views.ProjectViewSet").body[0].value
        assert _attribute_chain(tree) == ["views", "ProjectViewSet"]
        tree2 = ast.parse("foo").body[0].value
        assert _attribute_chain(tree2) == ["foo"]
        # 非 Name/Attribute 头部 → []
        tree3 = ast.parse("(1+2).foo").body[0].value
        assert _attribute_chain(tree3) == []

    def test_callable_name(self) -> None:
        tree = ast.parse("path('x', y)").body[0].value
        assert _callable_name(tree.func) == "path"
        tree2 = ast.parse("router.register('x', y)").body[0].value
        assert _callable_name(tree2.func) == "register"

    def test_is_include_call(self) -> None:
        node = ast.parse("include('apps.foo.urls')").body[0].value
        assert _is_include_call(node)
        bad = ast.parse("path('x', y)").body[0].value
        assert not _is_include_call(bad)

    def test_is_as_view_call(self) -> None:
        node = ast.parse("MyView.as_view()").body[0].value
        assert _is_as_view_call(node)
        bad = ast.parse("MyView()").body[0].value
        assert not _is_as_view_call(bad)


class TestRouteRecord:
    def test_to_dict(self) -> None:
        rec = RouteRecord(
            url_pattern="api/projects/",
            http_method="GET",
            view_module="apps.projects.views",
            view_class="ProjectViewSet",
            view_method="list",
            function_signature="apps.projects.views:ProjectViewSet.list",
            name="ProjectViewSet-list",
            source="router",
        )
        d = rec.to_dict()
        assert d["url_pattern"] == "api/projects/"
        assert d["http_method"] == "GET"
        assert d["source"] == "router"


# ----------------------------------------------------------------------
# fixture 仓库工厂
# ----------------------------------------------------------------------
@pytest.fixture
def repo_factory(tmp_path):
    """构造一个最小可解析的 Django 项目目录。"""

    def _factory(files: dict[str, str]) -> str:
        for rel, content in files.items():
            full = tmp_path / rel
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(textwrap.dedent(content), encoding="utf-8")
        # 兜底为每个目录补 __init__.py
        for rel in files:
            parts = rel.split("/")
            for i in range(1, len(parts)):
                init = tmp_path.joinpath(*parts[:i], "__init__.py")
                if not init.exists() and init.parent.is_dir():
                    init.write_text("", encoding="utf-8")
        return str(tmp_path)

    return _factory


# ----------------------------------------------------------------------
# 路由解析: ViewSet
# ----------------------------------------------------------------------
class TestRouterViewSet:
    def test_default_router_registers_viewset_actions(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/projects/__init__.py": "",
            "apps/projects/views.py": """
                from rest_framework import viewsets
                from rest_framework.decorators import action

                class ProjectViewSet(viewsets.ModelViewSet):
                    def list(self, request):
                        return None

                    def create(self, request):
                        return None

                    def retrieve(self, request, pk=None):
                        return None

                    @action(detail=True, methods=["post"])
                    def archive(self, request, pk=None):
                        return None

                    @action(detail=False, methods=["get"])
                    def dashboard(self, request):
                        return None
            """,
            "apps/projects/urls.py": """
                from rest_framework.routers import DefaultRouter
                from . import views

                router = DefaultRouter()
                router.register(r'projects', views.ProjectViewSet, basename='project')

                urlpatterns = router.urls
            """,
        })
        parser = DRFRouteParser(repo)
        records = parser.parse("apps.projects.urls")
        url_methods = {(r.url_pattern, r.http_method, r.view_method) for r in records}
        # 标准方法
        assert ("projects/", "GET", "list") in url_methods
        assert ("projects/", "POST", "create") in url_methods
        assert ("projects/{pk}/", "GET", "retrieve") in url_methods
        # @action(detail=True)
        assert ("projects/{pk}/archive/", "POST", "archive") in url_methods
        # @action(detail=False)
        assert ("projects/dashboard/", "GET", "dashboard") in url_methods

    def test_parse_to_dicts_serializable(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/x/__init__.py": "",
            "apps/x/views.py": """
                class ItemViewSet:
                    def list(self, request):
                        return None
            """,
            "apps/x/urls.py": """
                from rest_framework.routers import DefaultRouter
                from . import views

                router = DefaultRouter()
                router.register(r'items', views.ItemViewSet)
                urlpatterns = router.urls
            """,
        })
        parser = DRFRouteParser(repo)
        result = parser.parse_to_dicts("apps.x.urls")
        assert all(isinstance(r, dict) for r in result)
        assert any(r["view_method"] == "list" for r in result)


# ----------------------------------------------------------------------
# 路由解析: CBV (APIView 风格)
# ----------------------------------------------------------------------
class TestPathAsView:
    def test_cbv_expands_http_methods(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/health/__init__.py": "",
            "apps/health/views.py": """
                from rest_framework.views import APIView

                class HealthView(APIView):
                    def get(self, request):
                        return None

                    def post(self, request):
                        return None
            """,
            "apps/health/urls.py": """
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('health/', views.HealthView.as_view(), name='health'),
                ]
            """,
        })
        parser = DRFRouteParser(repo)
        records = parser.parse("apps.health.urls")
        methods = {(r.http_method, r.view_method) for r in records}
        assert ("GET", "get") in methods
        assert ("POST", "post") in methods
        # name 透传
        assert all(r.name == "health" for r in records)

    def test_cbv_no_methods_falls_back_to_any(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/empty/__init__.py": "",
            "apps/empty/views.py": """
                class StubView:
                    pass
            """,
            "apps/empty/urls.py": """
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('stub/', views.StubView.as_view()),
                ]
            """,
        })
        parser = DRFRouteParser(repo)
        records = parser.parse("apps.empty.urls")
        assert len(records) == 1
        assert records[0].http_method == "ANY"
        assert records[0].source == "path"


# ----------------------------------------------------------------------
# 路由解析: FBV
# ----------------------------------------------------------------------
class TestPathFBV:
    def test_function_view_recorded(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/util/__init__.py": "",
            "apps/util/views.py": """
                def ping(request):
                    return None
            """,
            "apps/util/urls.py": """
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('ping/', views.ping, name='ping'),
                ]
            """,
        })
        parser = DRFRouteParser(repo)
        records = parser.parse("apps.util.urls")
        assert len(records) == 1
        rec = records[0]
        assert rec.url_pattern == "ping/"
        assert rec.source == "fbv"
        assert rec.view_method == "ping"
        assert rec.http_method == "ANY"


# ----------------------------------------------------------------------
# include 递归
# ----------------------------------------------------------------------
class TestIncludeRecursion:
    def test_include_appends_prefix(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/users/__init__.py": "",
            "apps/users/views.py": """
                def login(request):
                    return None
            """,
            "apps/users/urls.py": """
                from django.urls import path
                from . import views

                urlpatterns = [
                    path('login/', views.login, name='login'),
                ]
            """,
            "config/__init__.py": "",
            "config/urls.py": """
                from django.urls import path, include

                urlpatterns = [
                    path('api/', include('apps.users.urls')),
                ]
            """,
        })
        parser = DRFRouteParser(repo)
        records = parser.parse("config.urls")
        assert len(records) == 1
        assert records[0].url_pattern == "api/login/"
        assert records[0].view_method == "login"

    def test_recursive_include_guard(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/loop/__init__.py": "",
            "apps/loop/urls.py": """
                from django.urls import path, include

                urlpatterns = [
                    path('a/', include('apps.loop.urls')),
                ]
            """,
        })
        parser = DRFRouteParser(repo)
        # 不应陷入死循环
        records = parser.parse("apps.loop.urls")
        assert isinstance(records, list)


# ----------------------------------------------------------------------
# 边界 / 异常
# ----------------------------------------------------------------------
class TestEdgeCases:
    def test_missing_module_returns_empty(self, repo_factory) -> None:
        repo = repo_factory({"placeholder.py": ""})
        parser = DRFRouteParser(repo)
        assert parser.parse("does.not.exist") == []

    def test_repo_path_missing(self, tmp_path) -> None:
        with pytest.raises(FileNotFoundError):
            DRFRouteParser(str(tmp_path / "missing"))

    def test_resolve_module_file_with_py_path(self, repo_factory) -> None:
        repo = repo_factory({
            "apps/__init__.py": "",
            "apps/util/__init__.py": "",
            "apps/util/views.py": "def ping(request):\n    return None\n",
            "apps/util/urls.py": (
                "from django.urls import path\n"
                "from . import views\n"
                "urlpatterns = [path('ping/', views.ping)]\n"
            ),
        })
        parser = DRFRouteParser(repo)
        # 直接用文件路径形式
        records = parser.parse("apps/util/urls.py")
        assert len(records) == 1
