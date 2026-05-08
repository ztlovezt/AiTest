from django.contrib import admin
from .models import (
    RepoBinding,
    CodeChangeAnalysis,
    TestCaseCodeMapping,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
)


@admin.register(RepoBinding)
class RepoBindingAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'repo_path', 'default_branch', 'is_active', 'created_at']
    list_filter = ['is_active', 'default_branch']
    search_fields = ['project__name', 'repo_path']


@admin.register(CodeChangeAnalysis)
class CodeChangeAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'repo_binding', 'base_commit', 'head_commit', 'status', 'progress', 'created_at']
    list_filter = ['status']
    search_fields = ['repo_binding__project__name', 'base_commit', 'head_commit']


@admin.register(TestCaseCodeMapping)
class TestCaseCodeMappingAdmin(admin.ModelAdmin):
    list_display = ['id', 'testcase', 'function_signature', 'mapping_type', 'confidence', 'created_at']
    list_filter = ['mapping_type']
    search_fields = ['testcase__title', 'function_signature', 'file_path']


@admin.register(ImpactAnalysis)
class ImpactAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'change_analysis', 'status', 'regression_time_estimate', 'created_at']
    list_filter = ['status']


@admin.register(RiskPredictionRecord)
class RiskPredictionRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'testcase', 'risk_score', 'risk_level', 'predicted_at']
    list_filter = ['risk_level']


@admin.register(PrecisionRunRecord)
class PrecisionRunRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'impact_analysis', 'reduction_rate', 'status', 'progress', 'created_at']
    list_filter = ['status']
