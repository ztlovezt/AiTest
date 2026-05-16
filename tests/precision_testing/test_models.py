"""精准测试模块 Django Model 单元测试。

覆盖目标:
    * RepoBinding — __str__ / ordering / db_table
    * CodeChangeAnalysis — status choices / __str__ / db_table
    * TestCaseCodeMapping — unique_together / __str__ / mapping_type choices
    * ImpactAnalysis — status choices / __str__
    * RiskPredictionRecord — risk_level choices / __str__
    * PrecisionRunRecord — status choices / __str__
    * 外键级联行为
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.precision_testing.models import (
    RepoBinding,
    CodeChangeAnalysis,
    TestCaseCodeMapping,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
)
from apps.projects.models import Project
from apps.testcases.models import TestCase

User = get_user_model()


# ----------------------------------------------------------------------
# RepoBinding
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestRepoBinding:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u1")
        project = Project.objects.create(name="P1", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/repo")
        assert str(repo) == "P1 -> /tmp/repo"

    def test_default_branch(self) -> None:
        user = User.objects.create_user(username="u2")
        project = Project.objects.create(name="P2", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        assert repo.default_branch == "main"

    def test_is_active_default(self) -> None:
        user = User.objects.create_user(username="u3")
        project = Project.objects.create(name="P3", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        assert repo.is_active is True

    def test_ordering_by_created_at_desc(self) -> None:
        assert RepoBinding._meta.ordering == ["-created_at"]

    def test_db_table(self) -> None:
        assert RepoBinding._meta.db_table == "precision_repo_bindings"

    def test_cascade_delete_with_project(self) -> None:
        user = User.objects.create_user(username="u4")
        project = Project.objects.create(name="P4", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        repo_id = repo.id
        project.delete()
        assert not RepoBinding.objects.filter(id=repo_id).exists()


# ----------------------------------------------------------------------
# CodeChangeAnalysis
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestCodeChangeAnalysis:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u5")
        project = Project.objects.create(name="P5", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abcdef1234567890", head_commit="1234567890abcdef"
        )
        assert str(analysis) == "P5: abcdef1..1234567"

    def test_status_default_pending(self) -> None:
        user = User.objects.create_user(username="u6")
        project = Project.objects.create(name="P6", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        assert analysis.status == "pending"

    def test_status_choices(self) -> None:
        choices = dict(CodeChangeAnalysis.STATUS_CHOICES)
        assert choices == {
            "pending": "排队中",
            "running": "分析中",
            "completed": "已完成",
            "failed": "失败",
        }

    def test_progress_default_zero(self) -> None:
        user = User.objects.create_user(username="u7")
        project = Project.objects.create(name="P7", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        assert analysis.progress == 0

    def test_changed_files_default_empty_list(self) -> None:
        user = User.objects.create_user(username="u8")
        project = Project.objects.create(name="P8", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        assert analysis.changed_files == []

    def test_db_table(self) -> None:
        assert CodeChangeAnalysis._meta.db_table == "precision_change_analyses"


# ----------------------------------------------------------------------
# TestCaseCodeMapping
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestTestCaseCodeMapping:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u9")
        project = Project.objects.create(name="P9", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC-Login", expected_result="ok", author=user
        )
        mapping = TestCaseCodeMapping.objects.create(
            testcase=testcase, function_signature="apps.auth:login", confidence=0.95
        )
        assert str(mapping) == "TC-Login -> apps.auth:login"

    def test_unique_together(self) -> None:
        # Django 5.x unique_together 返回 tuple of tuples
        assert ("testcase", "function_signature") in TestCaseCodeMapping._meta.unique_together

    def test_mapping_type_choices(self) -> None:
        choices = dict(TestCaseCodeMapping.MAPPING_TYPE_CHOICES)
        assert choices == {
            "manual": "手工映射",
            "auto_static": "静态分析",
            "auto_dynamic": "动态学习",
        }

    def test_confidence_default(self) -> None:
        user = User.objects.create_user(username="u10")
        project = Project.objects.create(name="P10", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC1", expected_result="ok", author=user
        )
        mapping = TestCaseCodeMapping.objects.create(
            testcase=testcase, function_signature="apps.foo:bar"
        )
        assert mapping.confidence == 1.0

    def test_cascade_delete_with_testcase(self) -> None:
        user = User.objects.create_user(username="u11")
        project = Project.objects.create(name="P11", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC2", expected_result="ok", author=user
        )
        mapping = TestCaseCodeMapping.objects.create(
            testcase=testcase, function_signature="apps.foo:bar"
        )
        mapping_id = mapping.id
        testcase.delete()
        assert not TestCaseCodeMapping.objects.filter(id=mapping_id).exists()


# ----------------------------------------------------------------------
# ImpactAnalysis
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestImpactAnalysis:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u12")
        project = Project.objects.create(name="P12", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="a", head_commit="b"
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        assert str(impact) == f"Impact of {analysis}"

    def test_status_default_pending(self) -> None:
        user = User.objects.create_user(username="u13")
        project = Project.objects.create(name="P13", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        assert impact.status == "pending"

    def test_impacted_functions_default_empty(self) -> None:
        user = User.objects.create_user(username="u14")
        project = Project.objects.create(name="P14", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        assert impact.impacted_functions == []

    def test_cascade_delete_with_analysis(self) -> None:
        user = User.objects.create_user(username="u15")
        project = Project.objects.create(name="P15", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        impact_id = impact.id
        analysis.delete()
        assert not ImpactAnalysis.objects.filter(id=impact_id).exists()


# ----------------------------------------------------------------------
# RiskPredictionRecord
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestRiskPredictionRecord:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u16")
        project = Project.objects.create(name="P16", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        testcase = TestCase.objects.create(
            project=project, title="TC-Risk", expected_result="ok", author=user
        )
        record = RiskPredictionRecord.objects.create(
            testcase=testcase, impact_analysis=impact, risk_score=0.85, risk_level="high"
        )
        assert str(record) == "TC-Risk: 0.85 (high)"

    def test_risk_level_default_low(self) -> None:
        user = User.objects.create_user(username="u17")
        project = Project.objects.create(name="P17", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        testcase = TestCase.objects.create(
            project=project, title="TC1", expected_result="ok", author=user
        )
        record = RiskPredictionRecord.objects.create(
            testcase=testcase, impact_analysis=impact, risk_score=0.5
        )
        assert record.risk_level == "low"

    def test_risk_level_choices(self) -> None:
        choices = dict(RiskPredictionRecord.RISK_LEVEL_CHOICES)
        assert set(choices.keys()) == {"low", "medium", "high", "critical"}

    def test_features_default_empty_dict(self) -> None:
        user = User.objects.create_user(username="u18")
        project = Project.objects.create(name="P18", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        testcase = TestCase.objects.create(
            project=project, title="TC2", expected_result="ok", author=user
        )
        record = RiskPredictionRecord.objects.create(
            testcase=testcase, impact_analysis=impact, risk_score=0.5
        )
        assert record.features == {}


# ----------------------------------------------------------------------
# PrecisionRunRecord
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestPrecisionRunRecord:
    def test_str_representation(self) -> None:
        user = User.objects.create_user(username="u19")
        project = Project.objects.create(name="P19", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=["TC-1"], total_testcases=10, reduction_rate=0.5
        )
        assert str(run) == f"Run {run.id}: 50.0% reduction"

    def test_status_default_pending(self) -> None:
        user = User.objects.create_user(username="u20")
        project = Project.objects.create(name="P20", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=[], total_testcases=10
        )
        assert run.status == "pending"

    def test_reduction_rate_default_zero(self) -> None:
        user = User.objects.create_user(username="u21")
        project = Project.objects.create(name="P21", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=[], total_testcases=10
        )
        assert run.reduction_rate == 0.0

    def test_progress_default_zero(self) -> None:
        user = User.objects.create_user(username="u22")
        project = Project.objects.create(name="P22", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=[], total_testcases=10
        )
        assert run.progress == 0

    def test_db_table(self) -> None:
        assert PrecisionRunRecord._meta.db_table == "precision_run_records"

    def test_cascade_delete_with_impact_analysis(self) -> None:
        user = User.objects.create_user(username="u23")
        project = Project.objects.create(name="P23", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(repo_binding=repo, base_commit="a", head_commit="b")
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=[], total_testcases=10
        )
        run_id = run.id
        impact.delete()
        assert not PrecisionRunRecord.objects.filter(id=run_id).exists()
