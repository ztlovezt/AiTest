"""精准测试模块 DRF 序列化器"""
from rest_framework import serializers
from .models import (
    RepoBinding,
    CodeChangeAnalysis,
    TestCaseCodeMapping,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
)


class RepoBindingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = RepoBinding
        fields = [
            'id', 'project', 'project_name', 'repo_path',
            'default_branch', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class CodeChangeAnalysisSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='repo_binding.project.name', read_only=True)

    class Meta:
        model = CodeChangeAnalysis
        fields = [
            'id', 'repo_binding', 'project_name', 'base_commit', 'head_commit',
            'changed_files', 'changed_functions', 'status', 'progress',
            'error_message', 'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = [
            'changed_files', 'changed_functions', 'status', 'progress',
            'error_message', 'started_at', 'completed_at', 'created_at',
        ]


class TestCaseCodeMappingSerializer(serializers.ModelSerializer):
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestCaseCodeMapping
        fields = [
            'id', 'testcase', 'testcase_title', 'function_signature',
            'file_path', 'mapping_type', 'confidence',
            'created_by', 'created_by_username', 'created_at',
        ]
        read_only_fields = ['created_at']


class ImpactAnalysisSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source='change_analysis.repo_binding.project.name', read_only=True
    )
    commit_range = serializers.SerializerMethodField()

    class Meta:
        model = ImpactAnalysis
        fields = [
            'id', 'change_analysis', 'project_name', 'commit_range',
            'impacted_functions', 'impacted_testcases',
            'min_regression_set', 'regression_time_estimate',
            'status', 'created_at',
        ]
        read_only_fields = ['status', 'created_at']

    def get_commit_range(self, obj: ImpactAnalysis) -> str:
        return (
            f"{obj.change_analysis.base_commit[:7]}.."
            f"{obj.change_analysis.head_commit[:7]}"
        )


class RiskPredictionRecordSerializer(serializers.ModelSerializer):
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)

    class Meta:
        model = RiskPredictionRecord
        fields = [
            'id', 'testcase', 'testcase_title', 'impact_analysis',
            'risk_score', 'risk_level', 'features', 'model_version', 'predicted_at',
        ]
        read_only_fields = ['predicted_at']


class PrecisionRunRecordSerializer(serializers.ModelSerializer):
    impact_commit_range = serializers.SerializerMethodField()

    class Meta:
        model = PrecisionRunRecord
        fields = [
            'id', 'impact_analysis', 'impact_commit_range',
            'selected_testcases', 'total_testcases', 'reduction_rate',
            'run_plan', 'status', 'progress',
            'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = [
            'status', 'progress', 'started_at', 'completed_at', 'created_at',
        ]

    def get_impact_commit_range(self, obj: PrecisionRunRecord) -> str:
        ca = obj.impact_analysis.change_analysis
        return f"{ca.base_commit[:7]}..{ca.head_commit[:7]}"
