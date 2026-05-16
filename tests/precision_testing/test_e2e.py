"""端到端流水线测试 — Week 4。

覆盖目标:
    * predict_risk_task — Risk 预测任务编排
    * run_precision_regression_task — 选集任务编排
    * trigger_pipeline 视图 — 输入校验
    * 预测 → 选集 → 持久化 完整链路
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ---------------------------------------------------------------------------
# 共享 fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_setup(db):
    """构造完整的精准测试上下文(project + impact + 用例 + 预测)。"""
    from apps.precision_testing.models import (
        CodeChangeAnalysis,
        ImpactAnalysis,
        RepoBinding,
    )
    from apps.projects.models import Project
    from apps.testcases.models import TestCase

    user = User.objects.create_user(username=f"e2e_{timezone.now().timestamp()}")
    project = Project.objects.create(name=f"E2EP_{timezone.now().timestamp()}", owner=user)
    binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
    analysis = CodeChangeAnalysis.objects.create(
        repo_binding=binding,
        base_commit="a" * 40,
        head_commit="b" * 40,
        status="completed",
    )

    cases = [
        TestCase.objects.create(
            project=project,
            title=f"e2e_tc_{i}",
            expected_result="ok",
            priority=p,
            author=user,
        )
        for i, p in enumerate(["critical", "high", "medium", "low"])
    ]
    impact = ImpactAnalysis.objects.create(
        change_analysis=analysis,
        impacted_testcases=[tc.id for tc in cases],
    )
    return {
        "user": user,
        "project": project,
        "binding": binding,
        "analysis": analysis,
        "impact": impact,
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Risk 预测任务
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPredictRiskTask:
    def test_writes_one_record_per_case(self, pipeline_setup) -> None:
        from apps.precision_testing.models import RiskPredictionRecord
        from apps.precision_testing.tasks import predict_risk_task

        impact = pipeline_setup["impact"]
        written = predict_risk_task(impact.id)
        assert written == len(pipeline_setup["cases"])
        assert RiskPredictionRecord.objects.filter(impact_analysis=impact).count() == len(
            pipeline_setup["cases"]
        )

    def test_critical_higher_score_than_low(self, pipeline_setup) -> None:
        from apps.precision_testing.models import RiskPredictionRecord
        from apps.precision_testing.tasks import predict_risk_task

        impact = pipeline_setup["impact"]
        predict_risk_task(impact.id)
        crit_case = next(tc for tc in pipeline_setup["cases"] if tc.priority == "critical")
        low_case = next(tc for tc in pipeline_setup["cases"] if tc.priority == "low")
        crit_record = RiskPredictionRecord.objects.get(
            impact_analysis=impact, testcase=crit_case
        )
        low_record = RiskPredictionRecord.objects.get(
            impact_analysis=impact, testcase=low_case
        )
        assert crit_record.risk_score > low_record.risk_score

    def test_no_impacted_cases_returns_zero(self, db) -> None:
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
        )
        from apps.precision_testing.tasks import predict_risk_task
        from apps.projects.models import Project

        user = User.objects.create_user(username=f"emp_{timezone.now().timestamp()}")
        project = Project.objects.create(name="EmpP", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        assert predict_risk_task(impact.id) == 0

    def test_repredict_clears_old_records(self, pipeline_setup) -> None:
        from apps.precision_testing.models import RiskPredictionRecord
        from apps.precision_testing.tasks import predict_risk_task

        impact = pipeline_setup["impact"]
        predict_risk_task(impact.id)
        first_count = RiskPredictionRecord.objects.filter(impact_analysis=impact).count()
        # 二次预测 — 不应翻倍
        predict_risk_task(impact.id)
        second_count = RiskPredictionRecord.objects.filter(impact_analysis=impact).count()
        assert first_count == second_count


# ---------------------------------------------------------------------------
# 流水线 — 预测 + 选集
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPredictAndSelectFlow:
    def test_full_flow_writes_selection(self, pipeline_setup) -> None:
        from apps.precision_testing.models import PrecisionRunRecord
        from apps.precision_testing.tasks import (
            predict_risk_task,
            run_precision_regression_task,
        )

        impact = pipeline_setup["impact"]
        predict_risk_task(impact.id)

        run = PrecisionRunRecord.objects.create(impact_analysis=impact, status="pending")
        result = run_precision_regression_task(run.id)
        assert "selected_testcase_ids" in result
        run.refresh_from_db()
        assert run.status == "completed"
        assert run.run_plan is not None

    def test_selection_persisted_on_impact(self, pipeline_setup) -> None:
        from apps.precision_testing.models import PrecisionRunRecord
        from apps.precision_testing.tasks import (
            predict_risk_task,
            run_precision_regression_task,
        )

        impact = pipeline_setup["impact"]
        predict_risk_task(impact.id)
        run = PrecisionRunRecord.objects.create(impact_analysis=impact, status="pending")
        run_precision_regression_task(run.id)
        impact.refresh_from_db()
        assert isinstance(impact.min_regression_set, list)
        assert impact.regression_time_estimate >= 0


# ---------------------------------------------------------------------------
# 视图层校验
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTriggerPipelineView:
    def _client(self):
        from rest_framework.test import APIClient

        client = APIClient()
        user = User.objects.create_user(
            username=f"vw_{timezone.now().timestamp()}",
            password="pwd",
        )
        client.force_authenticate(user=user)
        return client

    def test_missing_required_fields_returns_400(self) -> None:
        client = self._client()
        resp = client.post(
            "/api/precision-testing/runs/trigger-pipeline/",
            data={"repo_binding_id": 1},
            format="json",
        )
        assert resp.status_code == 400

    def test_force_full_without_reason_returns_400(self) -> None:
        client = self._client()
        resp = client.post(
            "/api/precision-testing/runs/trigger-pipeline/",
            data={
                "repo_binding_id": 1,
                "base_commit": "a" * 40,
                "head_commit": "b" * 40,
                "force_full": True,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "force_full_reason" in resp.json()["error"]

    def test_valid_request_dispatches_task(self) -> None:
        client = self._client()
        with patch(
            "apps.precision_testing.views.async_task", return_value="task-123"
        ) as mock_async:
            resp = client.post(
                "/api/precision-testing/runs/trigger-pipeline/",
                data={
                    "repo_binding_id": 1,
                    "base_commit": "a" * 40,
                    "head_commit": "b" * 40,
                },
                format="json",
            )
        assert resp.status_code == 202
        assert resp.json()["task_id"] == "task-123"
        mock_async.assert_called_once()


# ---------------------------------------------------------------------------
# bulk-create / import-csv 视图
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMappingBulkAndCsv:
    def _client_and_case(self):
        from apps.projects.models import Project
        from apps.testcases.models import TestCase
        from rest_framework.test import APIClient

        client = APIClient()
        user = User.objects.create_user(
            username=f"bulk_{timezone.now().timestamp()}",
            password="pwd",
        )
        client.force_authenticate(user=user)
        project = Project.objects.create(name="BulkP", owner=user)
        tc = TestCase.objects.create(
            project=project, title="bulk_tc", expected_result="ok", author=user
        )
        return client, tc

    def test_bulk_create_inserts_records(self) -> None:
        client, tc = self._client_and_case()
        resp = client.post(
            "/api/precision-testing/mappings/bulk-create/",
            data={
                "mappings": [
                    {
                        "testcase": tc.id,
                        "function_signature": "apps.x:f1",
                        "file_path": "x.py",
                        "mapping_type": "manual",
                        "confidence": 1.0,
                    },
                    {
                        "testcase": tc.id,
                        "function_signature": "apps.x:f2",
                        "file_path": "x.py",
                        "mapping_type": "manual",
                        "confidence": 0.8,
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["created"] == 2
        assert body["total"] == 2

    def test_csv_import_with_rows(self) -> None:
        client, tc = self._client_and_case()
        resp = client.post(
            "/api/precision-testing/mappings/import-csv/",
            data={
                "rows": [
                    {
                        "testcase_id": tc.id,
                        "function_signature": "apps.x:f1",
                        "file_path": "x.py",
                        "mapping_type": "manual",
                        "confidence": "1.0",
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["created"] == 1

    def test_csv_import_with_invalid_row_returns_207(self) -> None:
        client, tc = self._client_and_case()
        resp = client.post(
            "/api/precision-testing/mappings/import-csv/",
            data={
                "rows": [
                    {
                        "testcase_id": tc.id,
                        "function_signature": "apps.x:f1",
                        "file_path": "x.py",
                        "mapping_type": "manual",
                        "confidence": "1.0",
                    },
                    {
                        "testcase_id": 999999,  # 不存在
                        "function_signature": "apps.x:f2",
                        "file_path": "x.py",
                        "mapping_type": "manual",
                        "confidence": "0.5",
                    },
                ]
            },
            format="json",
        )
        assert resp.status_code == 207  # MULTI_STATUS
        body = resp.json()
        assert body["errors"]
        assert body["created"] == 1
