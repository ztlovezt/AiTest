"""精准测试模块 API 视图单元测试。

覆盖目标:
    * GraphDataView    — GET 参数校验 / 子图 vs 概览 / Neo4j 不可用容错
    * ImpactQueryView  — POST 参数校验 / 深度限制 / 路径查询 / 空输入
    * DashboardView    — GET 聚合统计
    * GitWebhookView   — POST 无鉴权 / 参数校验 / RepoBinding 查找
    * CoverageGateView — POST 门禁逻辑
    * ViewSets         — 列表/详情/自定义 action 行为
    * 认证             — IsAuthenticated 拒绝匿名用户

策略:
    * 使用 APIRequestFactory + force_authenticate 避免启动完整 WSGI 栈
    * 使用 monkeypatch 替换 impact_query.get_impact_query 和 neo4j_client
    * 使用 @pytest.mark.django_db 处理 Django ORM 查询
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.precision_testing import views as views_module
from apps.precision_testing import impact_query as iq_module
from apps.precision_testing.models import (
    CodeChangeAnalysis,
    ImpactAnalysis,
    PrecisionRunRecord,
    RepoBinding,
    TestCaseCodeMapping,
)
from apps.precision_testing.views import (
    GraphDataView,
    ImpactQueryView,
    DashboardView,
    GitWebhookView,
    CoverageGateView,
    RepoBindingViewSet,
    CodeChangeAnalysisViewSet,
    TestCaseCodeMappingViewSet,
    ImpactAnalysisViewSet,
    RiskPredictionRecordViewSet,
    PrecisionRunRecordViewSet,
)
from apps.projects.models import Project
from apps.projects.project_list_views import user_projects_list
from apps.testcases.models import TestCase
from apps.unified_projects.models import MetaProject, MetaProjectMember, ProjectModule

User = get_user_model()


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def user():
    return User.objects.create_user(username="tester", password="testpass")


@pytest.fixture
def authenticated_request(api_factory, user):
    """返回一个已认证的 GET request factory。"""
    def _make(method: str, url: str, data=None, params=None):
        m = getattr(api_factory, method.lower())
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        req = m(url, data=data, format="json") if data else m(url)
        force_authenticate(req, user=user)
        return req
    return _make


@pytest.fixture
def fake_impact_query(monkeypatch):
    """将 get_impact_query 替换为返回 MagicMock 的工厂。"""
    mock_query = MagicMock()
    monkeypatch.setattr(iq_module, "get_impact_query", lambda: mock_query)
    return mock_query


# ----------------------------------------------------------------------
# Project list sync
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestUserProjectsList:
    def test_list_backfills_meta_project_created_from_admin(self, api_factory, user) -> None:
        meta_project = MetaProject.objects.create(
            name="NOVA",
            description="created in admin",
            status="active",
            owner=user,
        )

        req = api_factory.get("/api/projects/list/")
        force_authenticate(req, user=user)
        resp = user_projects_list(req)

        assert resp.status_code == status.HTTP_200_OK
        assert any(item["name"] == "NOVA" for item in resp.data["results"])
        assert Project.objects.filter(unified_meta_project=meta_project, name="NOVA").exists()
        assert ProjectModule.objects.filter(meta_project=meta_project, module_type="AI").exists()
        assert MetaProjectMember.objects.filter(meta_project=meta_project, user=user, role="owner").exists()

    def test_list_includes_meta_project_member_access(self, api_factory) -> None:
        owner = User.objects.create_user(username="meta_owner", password="testpass")
        member = User.objects.create_user(username="meta_member", password="testpass")
        meta_project = MetaProject.objects.create(
            name="Shared Meta Project",
            description="shared",
            status="active",
            owner=owner,
        )
        MetaProjectMember.objects.create(meta_project=meta_project, user=member, role="tester")

        req = api_factory.get("/api/projects/list/")
        force_authenticate(req, user=member)
        resp = user_projects_list(req)

        assert resp.status_code == status.HTTP_200_OK
        assert any(item["name"] == "Shared Meta Project" for item in resp.data["results"])
        assert Project.objects.filter(unified_meta_project=meta_project).exists()


# ----------------------------------------------------------------------
# GraphDataView
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestGraphDataView:
    def test_get_overview_returns_200(self, authenticated_request, fake_impact_query) -> None:
        fake_impact_query.query_overview.return_value = {
            "nodes": [{"data": {"id": "1"}}],
            "edges": [],
        }
        req = authenticated_request("get", "/api/precision-testing/graph/")
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["nodes"]
        fake_impact_query.query_overview.assert_called_once_with(node_type=None, limit=200)

    def test_get_subgraph_with_center(self, authenticated_request, fake_impact_query) -> None:
        fake_impact_query.query_subgraph.return_value = {"nodes": [], "edges": []}
        req = authenticated_request(
            "get", "/api/precision-testing/graph/", params={"center": "apps.foo:bar", "depth": "2", "limit": "50"}
        )
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        fake_impact_query.query_subgraph.assert_called_once_with(
            node_id="apps.foo:bar", node_label="Function", depth=2, node_limit=50
        )

    @pytest.mark.parametrize(
        "params,expected_error",
        [
            ({"limit": "abc"}, "limit/depth must be integers"),
            ({"depth": "xyz"}, "limit/depth must be integers"),
        ],
    )
    def test_invalid_limit_depth_returns_400(
        self, authenticated_request, params, expected_error
    ) -> None:
        req = authenticated_request("get", "/api/precision-testing/graph/", params=params)
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert expected_error in str(resp.data["error"])

    def test_node_type_passed_to_overview(self, authenticated_request, fake_impact_query) -> None:
        fake_impact_query.query_overview.return_value = {"nodes": [], "edges": []}
        req = authenticated_request(
            "get", "/api/precision-testing/graph/", params={"node_type": "Function"}
        )
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        fake_impact_query.query_overview.assert_called_once_with(node_type="Function", limit=200)

    def test_invalid_node_type_returns_400(self, authenticated_request, fake_impact_query) -> None:
        fake_impact_query.query_overview.side_effect = ValueError("未知节点类型")
        req = authenticated_request(
            "get", "/api/precision-testing/graph/", params={"node_type": "EvilLabel"}
        )
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_neo4j_unavailable_returns_empty(self, authenticated_request, fake_impact_query) -> None:
        from neo4j.exceptions import ServiceUnavailable
        fake_impact_query.query_overview.side_effect = ServiceUnavailable("down")
        req = authenticated_request("get", "/api/precision-testing/graph/")
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data == {"nodes": [], "edges": []}

    def test_anonymous_rejected(self, api_factory) -> None:
        req = api_factory.get("/api/precision-testing/graph/")
        resp = GraphDataView.as_view()(req)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ----------------------------------------------------------------------
# ImpactQueryView
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestImpactQueryView:
    def test_post_valid_returns_200(self, authenticated_request, fake_impact_query) -> None:
        from apps.precision_testing.impact_query import ImpactResult
        fake_impact_query.query_impact.return_value = ImpactResult(
            changed_functions=["sig1"],
            impacted_functions=["sig2"],
            impacted_testcases=["TC-1"],
            impacted_endpoints=["GET /api/foo"],
            depth=3,
            elapsed_ms=12.0,
        )
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": ["sig1"]},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["changed_functions"] == ["sig1"]
        assert resp.data["impacted_functions"] == ["sig2"]

    def test_empty_changed_functions_returns_400(self, authenticated_request) -> None:
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": []},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot be empty" in str(resp.data["error"])

    def test_missing_changed_functions_returns_400(self, authenticated_request) -> None:
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in str(resp.data["error"])

    def test_invalid_changed_functions_type_returns_400(self, authenticated_request) -> None:
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": "not-a-list"},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "list[str]" in str(resp.data["error"])

    def test_depth_clamped_and_passed(self, authenticated_request, fake_impact_query) -> None:
        from apps.precision_testing.impact_query import ImpactResult
        fake_impact_query.query_impact.return_value = ImpactResult(
            ["a"], [], [], [], 2, 0.0
        )
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": ["a"], "depth": 2},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        fake_impact_query.query_impact.assert_called_once_with(
            changed_function_ids=["a"], depth=2, include_paths=False
        )

    def test_invalid_depth_returns_400(self, authenticated_request) -> None:
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": ["a"], "depth": "not-int"},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "depth must be an integer" in str(resp.data["error"])

    def test_include_paths_passed(self, authenticated_request, fake_impact_query) -> None:
        from apps.precision_testing.impact_query import ImpactResult
        fake_impact_query.query_impact.return_value = ImpactResult(
            ["a"], [], [], [], 3, 0.0, propagation_paths=[{"path": ["a"], "hops": 1}]
        )
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": ["a"], "include_paths": True},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["propagation_paths"]
        fake_impact_query.query_impact.assert_called_once_with(
            changed_function_ids=["a"], depth=3, include_paths=True
        )

    def test_neo4j_unavailable_returns_fallback(self, authenticated_request, fake_impact_query) -> None:
        from neo4j.exceptions import ServiceUnavailable
        fake_impact_query.query_impact.side_effect = ServiceUnavailable("down")
        req = authenticated_request(
            "post", "/api/precision-testing/impact/query/",
            data={"changed_functions": ["sig1"]},
        )
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["neo4j_available"] is False
        assert resp.data["impacted_functions"] == []

    def test_anonymous_rejected(self, api_factory) -> None:
        req = api_factory.post("/api/precision-testing/impact/query/", data={"changed_functions": ["a"]}, format="json")
        resp = ImpactQueryView.as_view()(req)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ----------------------------------------------------------------------
# DashboardView
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestDashboardView:
    def test_get_returns_aggregations(self, api_factory, user) -> None:
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abc", head_commit="def", status="completed"
        )
        ImpactAnalysis.objects.create(change_analysis=analysis, status="completed")
        PrecisionRunRecord.objects.create(
            impact_analysis=ImpactAnalysis.objects.first(),
            selected_testcases=[],
            total_testcases=10,
            reduction_rate=0.5,
            status="completed",
        )

        req = api_factory.get("/api/precision-testing/dashboard/")
        force_authenticate(req, user=user)
        resp = DashboardView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert "total_analyses" in resp.data
        assert "avg_reduction_rate" in resp.data
        assert "recent_runs" in resp.data

    def test_anonymous_rejected(self, api_factory) -> None:
        req = api_factory.get("/api/precision-testing/dashboard/")
        resp = DashboardView.as_view()(req)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ----------------------------------------------------------------------
# GitWebhookView
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestGitWebhookView:
    def test_post_valid_triggers_analysis(self, api_factory, user, monkeypatch) -> None:
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo", is_active=True)

        async_mock = MagicMock(return_value="task-123")
        monkeypatch.setattr(views_module, "async_task", async_mock)

        req = api_factory.post(
            "/api/precision-testing/webhooks/git/",
            data={"repo_binding_id": repo.id, "before": "abc", "after": "def"},
            format="json",
        )
        resp = GitWebhookView.as_view()(req)
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.data["analysis_id"]
        assert resp.data["task_id"] == "task-123"

    def test_post_missing_params_returns_400(self, api_factory) -> None:
        req = api_factory.post(
            "/api/precision-testing/webhooks/git/",
            data={"before": "abc"},
            format="json",
        )
        resp = GitWebhookView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_nonexistent_repo_returns_404(self, api_factory) -> None:
        req = api_factory.post(
            "/api/precision-testing/webhooks/git/",
            data={"repo_binding_id": 99999, "before": "abc", "after": "def"},
            format="json",
        )
        resp = GitWebhookView.as_view()(req)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_no_authentication_required(self, api_factory) -> None:
        """Webhook 视图显式设置了空 permission_classes。"""
        req = api_factory.post(
            "/api/precision-testing/webhooks/git/",
            data={"repo_binding_id": 99999, "before": "abc", "after": "def"},
            format="json",
        )
        resp = GitWebhookView.as_view()(req)
        # 即使 repo 不存在也返回 404，而非 403，说明认证未拦截
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_400_BAD_REQUEST)


# ----------------------------------------------------------------------
# CoverageGateView
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestCoverageGateView:
    def test_post_valid_returns_gate_result(self, api_factory, user) -> None:
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abc", head_commit="def",
            changed_functions=["fn1", "fn2", "fn3"]
        )
        req = api_factory.post(
            "/api/precision-testing/gate/",
            data={"analysis_id": analysis.id, "threshold": 0.8},
            format="json",
        )
        force_authenticate(req, user=user)
        resp = CoverageGateView.as_view()(req)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["analysis_id"] == analysis.id
        assert "passed" in resp.data
        assert resp.data["impacted_functions"] == 3

    def test_post_missing_analysis_id_returns_400(self, api_factory, user) -> None:
        req = api_factory.post("/api/precision-testing/gate/", data={}, format="json")
        force_authenticate(req, user=user)
        resp = CoverageGateView.as_view()(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_post_nonexistent_analysis_returns_404(self, api_factory, user) -> None:
        req = api_factory.post(
            "/api/precision-testing/gate/",
            data={"analysis_id": 99999},
            format="json",
        )
        force_authenticate(req, user=user)
        resp = CoverageGateView.as_view()(req)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_anonymous_rejected(self, api_factory) -> None:
        req = api_factory.post("/api/precision-testing/gate/", data={"analysis_id": 1}, format="json")
        resp = CoverageGateView.as_view()(req)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ----------------------------------------------------------------------
# ViewSets — 认证与列表
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestRepoBindingViewSet:
    def test_list_returns_200(self, api_factory, user) -> None:
        req = api_factory.get("/api/precision-testing/repos/")
        force_authenticate(req, user=user)
        resp = RepoBindingViewSet.as_view({"get": "list"})(req)
        assert resp.status_code == status.HTTP_200_OK

    def test_list_returns_frontend_fields(self, api_factory, user) -> None:
        project = Project.objects.create(name="Precision Repo", owner=user)
        RepoBinding.objects.create(
            project=project,
            name="TestNova",
            repo_url="https://github.com/testhub/testnova.git",
            repo_path="/tmp/testnova",
            default_branch="main",
        )

        req = api_factory.get("/api/precision-testing/repos/")
        force_authenticate(req, user=user)
        resp = RepoBindingViewSet.as_view({"get": "list"})(req)

        assert resp.status_code == status.HTTP_200_OK
        row = resp.data["results"][0]
        assert row["name"] == "TestNova"
        assert row["repo_url"] == "https://github.com/testhub/testnova.git"
        assert row["branch"] == "main"
        assert row["local_path"] == "/tmp/testnova"
        assert row["project_name"] == "Precision Repo"
        assert "last_analyzed_at" in row

    def test_list_supports_search(self, api_factory, user) -> None:
        project_a = Project.objects.create(name="Project Alpha", owner=user)
        project_b = Project.objects.create(name="Project Beta", owner=user)
        RepoBinding.objects.create(project=project_a, name="backend-service", repo_path="/tmp/a")
        RepoBinding.objects.create(project=project_b, name="frontend-console", repo_path="/tmp/b")

        req = api_factory.get("/api/precision-testing/repos/?search=backend")
        force_authenticate(req, user=user)
        resp = RepoBindingViewSet.as_view({"get": "list"})(req)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["name"] == "backend-service"

    def test_anonymous_rejected(self, api_factory) -> None:
        req = api_factory.get("/api/precision-testing/repos/")
        resp = RepoBindingViewSet.as_view({"get": "list"})(req)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCodeChangeAnalysisViewSet:
    def test_progress_action(self, api_factory, user) -> None:
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abc", head_commit="def", status="running", progress=50
        )
        req = api_factory.get(f"/api/precision-testing/analyses/{analysis.id}/progress/")
        force_authenticate(req, user=user)
        resp = CodeChangeAnalysisViewSet.as_view({"get": "progress"})(req, pk=analysis.id)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["progress"] == 50
        assert resp.data["status"] == "running"


@pytest.mark.django_db
class TestTestCaseCodeMappingViewSet:
    def test_auto_build_action_requires_repo_binding_id(self, api_factory, user) -> None:
        req = api_factory.post("/api/precision-testing/mappings/auto-build/", data={}, format="json")
        force_authenticate(req, user=user)
        resp = TestCaseCodeMappingViewSet.as_view({"post": "auto_build"})(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "repo_binding_id" in str(resp.data["error"])

    def test_auto_build_triggers_task(self, api_factory, user, monkeypatch) -> None:
        async_mock = MagicMock(return_value="task-456")
        monkeypatch.setattr(views_module, "async_task", async_mock)
        req = api_factory.post(
            "/api/precision-testing/mappings/auto-build/",
            data={"repo_binding_id": 1},
            format="json",
        )
        force_authenticate(req, user=user)
        resp = TestCaseCodeMappingViewSet.as_view({"post": "auto_build"})(req)
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.data["task_id"] == "task-456"


@pytest.mark.django_db
class TestRiskPredictionRecordViewSet:
    def test_trigger_action_requires_impact_analysis_id(self, api_factory, user) -> None:
        req = api_factory.post("/api/precision-testing/predictions/trigger/", data={}, format="json")
        force_authenticate(req, user=user)
        resp = RiskPredictionRecordViewSet.as_view({"post": "trigger"})(req)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "impact_analysis_id" in str(resp.data["error"])

    def test_trigger_triggers_task(self, api_factory, user, monkeypatch) -> None:
        async_mock = MagicMock(return_value="task-789")
        monkeypatch.setattr(views_module, "async_task", async_mock)
        req = api_factory.post(
            "/api/precision-testing/predictions/trigger/",
            data={"impact_analysis_id": 1},
            format="json",
        )
        force_authenticate(req, user=user)
        resp = RiskPredictionRecordViewSet.as_view({"post": "trigger"})(req)
        assert resp.status_code == status.HTTP_202_ACCEPTED
        assert resp.data["task_id"] == "task-789"


@pytest.mark.django_db
class TestPrecisionRunRecordViewSet:
    def test_create_triggers_async_task(self, api_factory, user, monkeypatch) -> None:
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo")
        analysis_obj = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="a", head_commit="b"
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis_obj)

        async_mock = MagicMock(return_value="task-run-1")
        monkeypatch.setattr(views_module, "async_task", async_mock)

        req = api_factory.post(
            "/api/precision-testing/runs/",
            data={"impact_analysis": impact.id, "selected_testcases": [], "total_testcases": 10},
            format="json",
        )
        force_authenticate(req, user=user)
        resp = PrecisionRunRecordViewSet.as_view({"post": "create"})(req)
        assert resp.status_code == status.HTTP_201_CREATED
