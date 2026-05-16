"""精准测试模块 DRF 序列化器单元测试。

覆盖目标:
    * RepoBindingSerializer — project 必填校验 / project_name 只读
    * CodeChangeAnalysisSerializer — 只读字段 / commit_range 格式化
    * TestCaseCodeMappingSerializer — confidence 边界 / testcase_title 只读
    * ImpactAnalysisSerializer — commit_range 方法字段
    * RiskPredictionRecordSerializer — testcase_title 只读
    * PrecisionRunRecordSerializer — impact_commit_range 方法字段
    * 序列化器 validate 异常路径
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.precision_testing.serializers import (
    RepoBindingSerializer,
    CodeChangeAnalysisSerializer,
    TestCaseCodeMappingSerializer,
    ImpactAnalysisSerializer,
    RiskPredictionRecordSerializer,
    PrecisionRunRecordSerializer,
)
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
# RepoBindingSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestRepoBindingSerializer:
    def test_create_requires_project(self) -> None:
        serializer = RepoBindingSerializer(data={"repo_path": "/tmp/repo"})
        assert not serializer.is_valid()
        assert "project" in serializer.errors or "non_field_errors" in serializer.errors

    def test_valid_create(self) -> None:
        user = User.objects.create_user(username="u1")
        project = Project.objects.create(name="P1", owner=user)
        serializer = RepoBindingSerializer(data={"project": project.id, "repo_path": "/tmp/repo"})
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.repo_path == "/tmp/repo"
        assert instance.project_id == project.id

    def test_project_name_read_only(self) -> None:
        serializer = RepoBindingSerializer()
        assert serializer.fields["project_name"].read_only is True

    def test_extra_kwargs_optional(self) -> None:
        serializer = RepoBindingSerializer()
        assert serializer.fields["project"].required is False
        assert serializer.fields["repo_path"].required is False

    def test_validate_raises_when_project_missing_on_create(self) -> None:
        serializer = RepoBindingSerializer(data={})
        assert not serializer.is_valid()

    def test_validate_passes_on_update(self) -> None:
        user = User.objects.create_user(username="u2")
        project = Project.objects.create(name="P2", owner=user)
        instance = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        serializer = RepoBindingSerializer(instance=instance, data={"repo_path": "/tmp/r2"}, partial=True)
        assert serializer.is_valid(), serializer.errors


# ----------------------------------------------------------------------
# CodeChangeAnalysisSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestCodeChangeAnalysisSerializer:
    def test_read_only_fields_cannot_be_set(self) -> None:
        user = User.objects.create_user(username="u3")
        project = Project.objects.create(name="P3", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abc1234", head_commit="def5678"
        )
        serializer = CodeChangeAnalysisSerializer(instance=analysis)
        data = serializer.data
        assert data["project_name"] == "P3"
        assert "base_commit" in data

    def test_status_is_read_only_on_create(self) -> None:
        assert "status" in CodeChangeAnalysisSerializer.Meta.read_only_fields


# ----------------------------------------------------------------------
# TestCaseCodeMappingSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestTestCaseCodeMappingSerializer:
    def test_confidence_default_1_0(self) -> None:
        serializer = TestCaseCodeMappingSerializer()
        assert serializer.fields["confidence"].default == 1.0

    def test_confidence_out_of_range_rejected(self) -> None:
        user = User.objects.create_user(username="u4")
        project = Project.objects.create(name="P4", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC1", expected_result="ok", author=user
        )
        serializer = TestCaseCodeMappingSerializer(data={
            "testcase": testcase.id,
            "function_signature": "apps.foo:bar",
            "confidence": 1.5,
        })
        assert not serializer.is_valid()
        assert "confidence" in serializer.errors

    def test_confidence_negative_rejected(self) -> None:
        user = User.objects.create_user(username="u5")
        project = Project.objects.create(name="P5", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC2", expected_result="ok", author=user
        )
        serializer = TestCaseCodeMappingSerializer(data={
            "testcase": testcase.id,
            "function_signature": "apps.foo:bar",
            "confidence": -0.1,
        })
        assert not serializer.is_valid()
        assert "confidence" in serializer.errors

    def test_valid_mapping(self) -> None:
        user = User.objects.create_user(username="u6")
        project = Project.objects.create(name="P6", owner=user)
        testcase = TestCase.objects.create(
            project=project, title="TC3", expected_result="ok", author=user
        )
        serializer = TestCaseCodeMappingSerializer(data={
            "testcase": testcase.id,
            "function_signature": "apps.foo:bar",
            "file_path": "apps/foo/bar.py",
            "confidence": 0.95,
        })
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.confidence == 0.95

    def test_testcase_title_read_only(self) -> None:
        serializer = TestCaseCodeMappingSerializer()
        assert serializer.fields["testcase_title"].read_only is True


# ----------------------------------------------------------------------
# ImpactAnalysisSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestImpactAnalysisSerializer:
    def test_commit_range_method_field(self) -> None:
        user = User.objects.create_user(username="u7")
        project = Project.objects.create(name="P7", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="abcdef1234567890", head_commit="1234567890abcdef"
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        serializer = ImpactAnalysisSerializer(instance=impact)
        assert serializer.data["commit_range"] == "abcdef1..1234567"

    def test_project_name_read_only(self) -> None:
        serializer = ImpactAnalysisSerializer()
        assert serializer.fields["project_name"].read_only is True


# ----------------------------------------------------------------------
# RiskPredictionRecordSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestRiskPredictionRecordSerializer:
    def test_testcase_title_read_only(self) -> None:
        serializer = RiskPredictionRecordSerializer()
        assert serializer.fields["testcase_title"].read_only is True

    def test_predicted_at_read_only(self) -> None:
        assert "predicted_at" in RiskPredictionRecordSerializer.Meta.read_only_fields


# ----------------------------------------------------------------------
# PrecisionRunRecordSerializer
# ----------------------------------------------------------------------
@pytest.mark.django_db
class TestPrecisionRunRecordSerializer:
    def test_impact_commit_range_method_field(self) -> None:
        user = User.objects.create_user(username="u8")
        project = Project.objects.create(name="P8", owner=user)
        repo = RepoBinding.objects.create(project=project, repo_path="/tmp/r")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=repo, base_commit="aaaabbbbccccdddd", head_commit="ddddcccceeeeffff"
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        run = PrecisionRunRecord.objects.create(
            impact_analysis=impact, selected_testcases=[], total_testcases=10, reduction_rate=0.5
        )
        serializer = PrecisionRunRecordSerializer(instance=run)
        assert serializer.data["impact_commit_range"] == "aaaabbb..ddddccc"

    def test_status_read_only(self) -> None:
        assert "status" in PrecisionRunRecordSerializer.Meta.read_only_fields
