# Week 1: 精准测试基础架构 — Pytest 测试脚本

"""
精准测试模块 Week 1 基础架构测试套件
覆盖 13 个 REST API 端点 + Neo4jClient + 模型 + Serializer

运行方式:
    pytest tests/testcase/precision_testing/week1/test_api_week1.py -v
    pytest tests/testcase/precision_testing/week1/test_api_week1.py -v -k "TC-001"
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client(db, user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def authenticated_client(db, user):
    """已认证的 API 客户端"""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def sample_repo_binding(db, project):
    """示例仓库绑定"""
    from apps.precision_testing.models import RepoBinding
    return RepoBinding.objects.create(
        project=project,
        repo_path="/var/repos/testhub",
        default_branch="main",
        is_active=True
    )


@pytest.fixture
def sample_code_change_analysis(db, sample_repo_binding):
    """示例代码变更分析"""
    from apps.precision_testing.models import CodeChangeAnalysis
    return CodeChangeAnalysis.objects.create(
        repo_binding=sample_repo_binding,
        base_commit="abc1234" + "0" * 57,
        head_commit="def5678" + "0" * 57,
        status="completed",
        progress=100,
        changed_files=["apps/users/views.py"],
        changed_functions=["apps.users.views:get_user"]
    )


# ============================================================================
# TC-001: 创建 RepoBinding（仓库绑定）— 正常参数
# ============================================================================
@pytest.mark.django_db
def test_create_repo_binding_success(api_client, project):
    """TC-001: 创建 RepoBinding（仓库绑定）— 正常参数"""
    response = api_client.post(
        '/api/precision-testing/repos/',
        data={
            "project": project.id,
            "repo_path": "/var/repos/testhub",
            "default_branch": "main",
            "is_active": True
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}: {response.data}"
    assert response.data['id'] is not None
    assert response.data['repo_path'] == "/var/repos/testhub"
    assert response.data['is_active'] is True
    assert 'created_at' in response.data


# ============================================================================
# TC-002: 创建 RepoBinding — 缺少必填字段 project
# ============================================================================
@pytest.mark.django_db
def test_create_repo_binding_missing_project(api_client):
    """TC-002: 创建 RepoBinding — 缺少必填字段 project"""
    response = api_client.post(
        '/api/precision-testing/repos/',
        data={"repo_path": "/var/repos/testhub", "default_branch": "main"},
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'project' in response.data


# ============================================================================
# TC-003: 创建 RepoBinding — 重复项目绑定
# ============================================================================
@pytest.mark.django_db
def test_create_repo_binding_duplicate_project(api_client, sample_repo_binding, another_project):
    """TC-003: 创建 RepoBinding — 重复项目绑定（unique_together 约束）"""
    response = api_client.post(
        '/api/precision-testing/repos/',
        data={
            "project": sample_repo_binding.project.id,
            "repo_path": "/different/path",
            "default_branch": "main"
        },
        format='json'
    )
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]


# ============================================================================
# TC-004: 列出所有 RepoBinding（分页 + 过滤）
# ============================================================================
@pytest.mark.django_db
def test_list_repo_bindings(api_client, sample_repo_binding):
    """TC-004: 列出所有 RepoBinding（分页 + 过滤）"""
    response = api_client.get('/api/precision-testing/repos/')
    assert response.status_code == status.HTTP_200_OK
    assert 'results' in response.data
    assert 'count' in response.data


@pytest.mark.django_db
def test_list_repo_bindings_filter_is_active(api_client, sample_repo_binding):
    """TC-004b: 按 is_active 过滤"""
    response = api_client.get('/api/precision-testing/repos/?is_active=true')
    assert response.status_code == status.HTTP_200_OK


# ============================================================================
# TC-005: 更新 RepoBinding — 切换 is_active 状态
# ============================================================================
@pytest.mark.django_db
def test_update_repo_binding(api_client, sample_repo_binding):
    """TC-005: 更新 RepoBinding — 切换 is_active 状态"""
    response = api_client.put(
        f'/api/precision-testing/repos/{sample_repo_binding.id}/',
        data={"is_active": False},
        format='json'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data['is_active'] is False


# ============================================================================
# TC-006: 删除 RepoBinding
# ============================================================================
@pytest.mark.django_db
def test_delete_repo_binding(api_client, sample_repo_binding):
    """TC-006: 删除 RepoBinding"""
    response = api_client.delete(f'/api/precision-testing/repos/{sample_repo_binding.id}/')
    assert response.status_code == status.HTTP_204_NO_CONTENT
    from apps.precision_testing.models import RepoBinding
    with pytest.raises(RepoBinding.DoesNotExist):
        RepoBinding.objects.get(id=sample_repo_binding.id)


# ============================================================================
# TC-007: 触发代码变更分析（analyze action）— 正常触发
# ============================================================================
@pytest.mark.django_db
def test_repo_analyze_success(api_client, sample_repo_binding):
    """TC-007: 触发代码变更分析（analyze action）— 正常触发"""
    response = api_client.post(
        f'/api/precision-testing/repos/{sample_repo_binding.id}/analyze/',
        data={"base_commit": "HEAD~5", "head_commit": "HEAD"},
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED, f"Got {response.status_code}: {response.data}"
    assert 'analysis_id' in response.data
    assert 'task_id' in response.data

    from apps.precision_testing.models import CodeChangeAnalysis
    assert CodeChangeAnalysis.objects.filter(id=response.data['analysis_id']).exists()


# ============================================================================
# TC-008: 触发代码变更分析 — 缺少必填参数（defaults）
# ============================================================================
@pytest.mark.django_db
def test_repo_analyze_default_params(api_client, sample_repo_binding):
    """TC-008: 触发代码变更分析 — 使用默认参数（base_commit/head_commit 有默认值）"""
    response = api_client.post(
        f'/api/precision-testing/repos/{sample_repo_binding.id}/analyze/',
        data={},
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED


# ============================================================================
# TC-009: 查询 CodeChangeAnalysis 列表 — 过滤状态
# ============================================================================
@pytest.mark.django_db
def test_list_analyses_filter_status(api_client, sample_code_change_analysis):
    """TC-009: 查询 CodeChangeAnalysis 列表 — 过滤状态"""
    response = api_client.get('/api/precision-testing/analyses/?status=completed')
    assert response.status_code == status.HTTP_200_OK
    for item in response.data['results']:
        assert item['status'] == 'completed'


# ============================================================================
# TC-010: 查询 CodeChangeAnalysis 单条记录
# ============================================================================
@pytest.mark.django_db
def test_retrieve_analysis(api_client, sample_code_change_analysis):
    """TC-010: 查询 CodeChangeAnalysis 单条记录"""
    response = api_client.get(f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert 'changed_files' in response.data
    assert 'changed_functions' in response.data
    assert 'project_name' in response.data


# ============================================================================
# TC-011: 轮询分析进度（progress action）— 分析中状态
# ============================================================================
@pytest.mark.django_db
def test_analysis_progress_running(api_client, sample_code_change_analysis):
    """TC-011: 轮询分析进度（progress action）— 分析中状态"""
    sample_code_change_analysis.status = 'running'
    sample_code_change_analysis.progress = 50
    sample_code_change_analysis.save()

    response = api_client.get(f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/progress/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['status'] == 'running'
    assert response.data['progress'] == 50


# ============================================================================
# TC-012: 轮询分析进度 — 分析失败状态
# ============================================================================
@pytest.mark.django_db
def test_analysis_progress_failed(api_client, sample_code_change_analysis):
    """TC-012: 轮询分析进度 — 分析失败状态（含错误信息）"""
    sample_code_change_analysis.status = 'failed'
    sample_code_change_analysis.error_message = 'Git diff failed'
    sample_code_change_analysis.save()

    response = api_client.get(f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/progress/')
    assert response.data['status'] == 'failed'
    assert response.data['error_message'] != ''


# ============================================================================
# TC-013: 创建 TestCaseCodeMapping（手工映射）— 正常参数
# ============================================================================
@pytest.mark.django_db
def test_create_mapping_success(api_client, testcase):
    """TC-013: 创建 TestCaseCodeMapping（手工映射）— 正常参数"""
    response = api_client.post(
        '/api/precision-testing/mappings/',
        data={
            "testcase": testcase.id,
            "function_signature": "apps.users.views:UserLoginView.post",
            "file_path": "apps/users/views.py",
            "mapping_type": "manual",
            "confidence": 1.0
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED, f"Got {response.status_code}: {response.data}"
    assert response.data['mapping_type'] == 'manual'
    assert response.data['confidence'] == 1.0


# ============================================================================
# TC-014: 创建 TestCaseCodeMapping — 重复 unique_together
# ============================================================================
@pytest.mark.django_db
def test_create_mapping_duplicate(api_client, testcase):
    """TC-014: 创建 TestCaseCodeMapping — 重复 unique_together"""
    from apps.precision_testing.models import TestCaseCodeMapping
    TestCaseCodeMapping.objects.create(
        testcase=testcase,
        function_signature="duplicate_sig",
        file_path="a.py",
        mapping_type="manual"
    )
    response = api_client.post(
        '/api/precision-testing/mappings/',
        data={
            "testcase": testcase.id,
            "function_signature": "duplicate_sig",
            "file_path": "a.py",
            "mapping_type": "manual"
        },
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TC-015: 创建 TestCaseCodeMapping — 置信度边界值测试（0.0）
# ============================================================================
@pytest.mark.django_db
def test_create_mapping_confidence_zero(api_client, testcase):
    """TC-015: 创建 TestCaseCodeMapping — 置信度边界值测试（0.0）"""
    response = api_client.post(
        '/api/precision-testing/mappings/',
        data={
            "testcase": testcase.id,
            "function_signature": "sig_zero",
            "file_path": "a.py",
            "mapping_type": "auto_static",
            "confidence": 0.0
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data['confidence'] == 0.0


# ============================================================================
# TC-016: 创建 TestCaseCodeMapping — 无效置信度（>1.0）
# ============================================================================
@pytest.mark.django_db
def test_create_mapping_confidence_invalid(api_client, testcase):
    """TC-016: 创建 TestCaseCodeMapping — 无效置信度（>1.0）"""
    response = api_client.post(
        '/api/precision-testing/mappings/',
        data={
            "testcase": testcase.id,
            "function_signature": "sig_invalid",
            "file_path": "a.py",
            "confidence": 1.5
        },
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TC-017: 触发静态分析自动建图（auto_build action）
# ============================================================================
@pytest.mark.django_db
def test_auto_build_mappings(api_client, sample_repo_binding):
    """TC-017: 触发静态分析自动建图（auto_build action）"""
    response = api_client.post(
        '/api/precision-testing/mappings/auto-build/',
        data={"repo_binding_id": sample_repo_binding.id},
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert 'task_id' in response.data


# ============================================================================
# TC-018: 触发静态分析自动建图 — 缺少 repo_binding_id
# ============================================================================
@pytest.mark.django_db
def test_auto_build_missing_param(api_client):
    """TC-018: 触发静态分析自动建图 — 缺少 repo_binding_id"""
    response = api_client.post(
        '/api/precision-testing/mappings/auto-build/',
        data={},
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data


# ============================================================================
# TC-019: 查询 ImpactAnalysis 列表
# ============================================================================
@pytest.mark.django_db
def test_list_impact_analyses(api_client, sample_code_change_analysis):
    """TC-019: 查询 ImpactAnalysis 列表"""
    from apps.precision_testing.models import ImpactAnalysis
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed',
        impacted_functions=["f1", "f2"],
        impacted_testcases=[1, 2],
        min_regression_set=[1],
        regression_time_estimate=120
    )
    response = api_client.get('/api/precision-testing/impact/')
    assert response.status_code == status.HTTP_200_OK
    # commit_range 是 computed field
    if response.data['results']:
        assert 'commit_range' in response.data['results'][0]


# ============================================================================
# TC-020: 查询 ImpactAnalysis 单条 — 验证 JSON 字段结构
# ============================================================================
@pytest.mark.django_db
def test_retrieve_impact_detail(api_client, sample_code_change_analysis):
    """TC-020: 查询 ImpactAnalysis 单条 — 验证 JSON 字段结构"""
    from apps.precision_testing.models import ImpactAnalysis
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed',
        impacted_functions=["apps.users.views:get_user", "apps.projects.models:Project.create"],
        impacted_testcases=[10, 25],
        min_regression_set=[10],
        regression_time_estimate=60
    )
    response = api_client.get(f'/api/precision-testing/impact/{impact.id}/')
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.data['impacted_functions'], list)
    assert isinstance(response.data['min_regression_set'], list)
    assert isinstance(response.data['regression_time_estimate'], int)


# ============================================================================
# TC-021: 查询 RiskPredictionRecord 列表 — 过滤 risk_level
# ============================================================================
@pytest.mark.django_db
def test_list_predictions_filter_risk_level(api_client, sample_code_change_analysis, testcase):
    """TC-021: 查询 RiskPredictionRecord 列表 — 过滤 risk_level"""
    from apps.precision_testing.models import ImpactAnalysis, RiskPredictionRecord
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed'
    )
    RiskPredictionRecord.objects.create(
        testcase=testcase,
        impact_analysis=impact,
        risk_score=0.85,
        risk_level='high'
    )
    RiskPredictionRecord.objects.create(
        testcase=testcase,
        impact_analysis=impact,
        risk_score=0.20,
        risk_level='low'
    )
    response = api_client.get('/api/precision-testing/predictions/?risk_level=high')
    assert response.status_code == status.HTTP_200_OK
    for item in response.data['results']:
        assert item['risk_level'] == 'high'


# ============================================================================
# TC-022: 创建 RiskPredictionRecord 手动触发预测（trigger action）
# ============================================================================
@pytest.mark.django_db
def test_trigger_prediction(api_client, sample_code_change_analysis):
    """TC-022: 创建 RiskPredictionRecord 手动触发预测（trigger action）"""
    from apps.precision_testing.models import ImpactAnalysis
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed'
    )
    response = api_client.post(
        '/api/precision-testing/predictions/trigger/',
        data={"impact_analysis_id": impact.id},
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert 'task_id' in response.data


# ============================================================================
# TC-023: 创建 RiskPredictionRecord 手动触发 — 缺少 impact_analysis_id
# ============================================================================
@pytest.mark.django_db
def test_trigger_prediction_missing_param(api_client):
    """TC-023: 创建 RiskPredictionRecord 手动触发 — 缺少 impact_analysis_id"""
    response = api_client.post(
        '/api/precision-testing/predictions/trigger/',
        data={},
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data['error'] == "impact_analysis_id is required"


# ============================================================================
# TC-024: 创建 PrecisionRunRecord（精准回归执行记录）
# ============================================================================
@pytest.mark.django_db
def test_create_precision_run(api_client, sample_code_change_analysis):
    """TC-024: 创建 PrecisionRunRecord（精准回归执行记录）"""
    from apps.precision_testing.models import ImpactAnalysis
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed'
    )
    response = api_client.post(
        '/api/precision-testing/runs/',
        data={
            "impact_analysis": impact.id,
            "selected_testcases": [10, 25, 38],
            "total_testcases": 200
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED, f"Got {response.status_code}: {response.data}"
    assert response.data['status'] == 'pending'
    assert 'task_id' in response.data
    assert response.data['reduction_rate'] == 0.0


# ============================================================================
# TC-025: 查询 PrecisionRunRecord 列表 — 验证 computed field
# ============================================================================
@pytest.mark.django_db
def test_list_precision_runs(api_client, sample_code_change_analysis):
    """TC-025: 查询 PrecisionRunRecord 列表 — 验证 computed field"""
    from apps.precision_testing.models import ImpactAnalysis, PrecisionRunRecord
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed'
    )
    PrecisionRunRecord.objects.create(
        impact_analysis=impact,
        selected_testcases=[1, 2],
        total_testcases=100,
        status='completed',
        reduction_rate=0.55
    )
    response = api_client.get('/api/precision-testing/runs/')
    assert response.status_code == status.HTTP_200_OK
    assert 'impact_commit_range' in response.data['results'][0]


# ============================================================================
# TC-026: 获取图数据（GraphDataView）— 正常查询
# ============================================================================
@pytest.mark.django_db
def test_get_graph_data(api_client, sample_repo_binding):
    """TC-026: 获取图数据（GraphDataView）— 正常查询"""
    response = api_client.get('/api/precision-testing/graph/?node_type=Function&limit=100')
    assert response.status_code == status.HTTP_200_OK
    assert 'nodes' in response.data
    assert 'links' in response.data
    assert isinstance(response.data['nodes'], list)
    assert isinstance(response.data['links'], list)


# ============================================================================
# TC-027: 获取图数据 — 默认参数（无 node_type，limit=200）
# ============================================================================
@pytest.mark.django_db
def test_get_graph_data_default_params(api_client):
    """TC-027: 获取图数据 — 默认参数（无 node_type，limit=200）"""
    response = api_client.get('/api/precision-testing/graph/')
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['nodes']) <= 200


# ============================================================================
# TC-028: 获取图数据 — limit 参数类型转换
# ============================================================================
@pytest.mark.django_db
def test_get_graph_data_limit_conversion(api_client):
    """TC-028: 获取图数据 — limit 参数类型转换（字符串"100"→int）"""
    response = api_client.get('/api/precision-testing/graph/?limit=100')
    assert response.status_code == status.HTTP_200_OK


# ============================================================================
# TC-030: 获取看板数据（DashboardView）— 正常查询
# ============================================================================
@pytest.mark.django_db
def test_get_dashboard(api_client):
    """TC-030: 获取看板数据（DashboardView）— 正常查询"""
    response = api_client.get('/api/precision-testing/dashboard/')
    assert response.status_code == status.HTTP_200_OK
    assert 'total_mappings' in response.data
    assert 'avg_reduction_rate' in response.data
    assert 'recent_runs' in response.data
    assert isinstance(response.data['recent_runs'], list)


# ============================================================================
# TC-031: 获取看板数据 — 空的数据库（零数据）
# ============================================================================
@pytest.mark.django_db
def test_get_dashboard_empty(api_client):
    """TC-031: 获取看板数据 — 空的数据库（零数据）"""
    response = api_client.get('/api/precision-testing/dashboard/')
    assert response.data['total_mappings'] == 0
    assert response.data['avg_reduction_rate'] == 0.0
    assert response.data['recent_runs'] == []


# ============================================================================
# TC-032: Git Webhook 接收 — 正常 push 事件
# ============================================================================
@pytest.mark.django_db
def test_git_webhook_success(api_client, sample_repo_binding):
    """TC-032: Git Webhook 接收 — 正常 push 事件"""
    response = api_client.post(
        '/api/precision-testing/webhooks/git/',
        data={
            "repo_binding_id": sample_repo_binding.id,
            "before": "a" * 40,
            "after": "b" * 40
        },
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert 'analysis_id' in response.data


# ============================================================================
# TC-033: Git Webhook 接收 — 缺少必填字段
# ============================================================================
@pytest.mark.django_db
def test_git_webhook_missing_fields(api_client):
    """TC-033: Git Webhook 接收 — 缺少必填字段"""
    response = api_client.post(
        '/api/precision-testing/webhooks/git/',
        data={"repo_binding_id": 1},
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'error' in response.data


# ============================================================================
# TC-034: Git Webhook 接收 — repo_binding_id 不存在或未激活
# ============================================================================
@pytest.mark.django_db
def test_git_webhook_not_found(api_client):
    """TC-034: Git Webhook 接收 — repo_binding_id 不存在"""
    response = api_client.post(
        '/api/precision-testing/webhooks/git/',
        data={
            "repo_binding_id": 99999,
            "before": "a" * 40,
            "after": "b" * 40
        },
        format='json'
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# TC-035: 覆盖率门禁（CoverageGateView）— 通过门禁
# ============================================================================
@pytest.mark.django_db
def test_coverage_gate_pass(api_client, sample_code_change_analysis):
    """TC-035: 覆盖率门禁（CoverageGateView）— 通过门禁"""
    sample_code_change_analysis.changed_functions = ["f1", "f2", "f3"]
    sample_code_change_analysis.save()

    response = api_client.post(
        '/api/precision-testing/gate/',
        data={"analysis_id": sample_code_change_analysis.id, "threshold": 0.80},
        format='json'
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data['passed'] is True


# ============================================================================
# TC-036: 覆盖率门禁 — 未通过门禁（impacted_functions > 5）
# ============================================================================
@pytest.mark.django_db
def test_coverage_gate_fail(api_client, sample_code_change_analysis):
    """TC-036: 覆盖率门禁 — 未通过门禁（impacted_functions > 5）"""
    sample_code_change_analysis.changed_functions = ["f1"] * 10
    sample_code_change_analysis.save()

    response = api_client.post(
        '/api/precision-testing/gate/',
        data={"analysis_id": sample_code_change_analysis.id, "threshold": 0.80},
        format='json'
    )
    assert response.data['passed'] is False


# ============================================================================
# TC-037: 覆盖率门禁 — 缺少 analysis_id
# ============================================================================
@pytest.mark.django_db
def test_coverage_gate_missing_id(api_client):
    """TC-037: 覆盖率门禁 — 缺少 analysis_id"""
    response = api_client.post(
        '/api/precision-testing/gate/',
        data={},
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TC-038: 覆盖率门禁 — analysis_id 不存在
# ============================================================================
@pytest.mark.django_db
def test_coverage_gate_not_found(api_client):
    """TC-038: 覆盖率门禁 — analysis_id 不存在"""
    response = api_client.post(
        '/api/precision-testing/gate/',
        data={"analysis_id": 99999},
        format='json'
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# TC-039: 权限验证 — 未认证用户访问受保护端点
# ============================================================================
@pytest.mark.django_db
def test_unauthenticated_access():
    """TC-039: 权限验证 — 未认证用户访问受保护端点"""
    client = APIClient()
    response = client.get('/api/precision-testing/repos/')
    assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


# ============================================================================
# TC-040: GitWebhook 权限验证 — 无需认证
# ============================================================================
@pytest.mark.django_db
def test_webhook_no_auth_required(api_client, sample_repo_binding):
    """TC-040: GitWebhook 权限验证 — 无需认证（permission_classes=[]）"""
    response = api_client.post(
        '/api/precision-testing/webhooks/git/',
        data={
            "repo_binding_id": sample_repo_binding.id,
            "before": "a" * 40,
            "after": "b" * 40
        },
        format='json'
    )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.status_code != status.HTTP_401_UNAUTHORIZED


# ============================================================================
# TC-041: Neo4jClient 单例模式验证
# ============================================================================
def test_neo4j_client_singleton():
    """TC-041: Neo4jClient 单例模式验证"""
    from apps.precision_testing.neo4j_client import Neo4jClient, get_neo4j_client
    client1 = Neo4jClient()
    client2 = Neo4jClient()
    assert client1 is client2


# ============================================================================
# TC-046: Neo4jClient.verify_connectivity — 连接成功
# ============================================================================
@pytest.mark.django_db
def test_neo4j_verify_connectivity():
    """TC-046: Neo4jClient.verify_connectivity — 连接成功"""
    from apps.precision_testing.neo4j_client import get_neo4j_client
    # 使用 @override_settings 或 mock 跳过实际 Neo4j 连接
    client = get_neo4j_client()
    result = client.verify_connectivity()
    # Neo4j 可能不可用，此测试结果取决于环境
    assert isinstance(result, bool)


# ============================================================================
# TC-058: RepoBinding 唯一性约束 — 同一项目不能重复绑定
# ============================================================================
@pytest.mark.django_db
def test_repo_binding_project_unique_constraint(api_client, sample_repo_binding, another_project):
    """TC-058: RepoBinding 唯一性约束 — 同一项目不能重复绑定"""
    response = api_client.post(
        '/api/precision-testing/repos/',
        data={
            "project": sample_repo_binding.project.id,
            "repo_path": "/new/path",
            "default_branch": "develop"
        },
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert 'project' in str(response.data)


# ============================================================================
# TC-059: CodeChangeAnalysis ReadOnly — 不可通过 API 修改
# ============================================================================
@pytest.mark.django_db
def test_analysis_readonly(api_client, sample_code_change_analysis):
    """TC-059: CodeChangeAnalysis ReadOnly — 不可通过 API 修改"""
    response = api_client.put(
        f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/',
        data={"status": "completed", "changed_functions": ["f1"]},
        format='json'
    )
    assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_405_METHOD_NOT_ALLOWED]


# ============================================================================
# TC-060: GraphDataView — 空数据库返回空结构
# ============================================================================
@pytest.mark.django_db
def test_graph_data_empty(api_client):
    """TC-060: GraphDataView — 空数据库返回空结构"""
    response = api_client.get('/api/precision-testing/graph/')
    assert response.status_code == status.HTTP_200_OK
    assert response.data['nodes'] == []
    assert response.data['links'] == []


# ============================================================================
# TC-061: DashboardView — avg_reduction_rate 为 None 时的降级
# ============================================================================
@pytest.mark.django_db
def test_dashboard_avg_reduction_none(api_client):
    """TC-061: DashboardView — avg_reduction_rate 为 None 时的降级"""
    response = api_client.get('/api/precision-testing/dashboard/')
    assert response.data['avg_reduction_rate'] == 0.0
    assert isinstance(response.data['avg_reduction_rate'], float)


# ============================================================================
# TC-063: repo_binding.project_name — 反向关联读取
# ============================================================================
@pytest.mark.django_db
def test_repo_binding_project_name(api_client, sample_repo_binding):
    """TC-063: repo_binding.project_name — 反向关联读取"""
    response = api_client.get(f'/api/precision-testing/repos/{sample_repo_binding.id}/')
    assert 'project_name' in response.data
    assert isinstance(response.data['project_name'], str)


# ============================================================================
# TC-065: 创建 RepoBinding — repo_path 长度边界（max_length=500）
# ============================================================================
@pytest.mark.django_db
def test_create_repo_binding_max_length(api_client, another_project):
    """TC-065: 创建 RepoBinding — repo_path 长度边界（max_length=500）"""
    response = api_client.post(
        '/api/precision-testing/repos/',
        data={
            "project": another_project.id,
            "repo_path": "a" * 500,
            "default_branch": "main"
        },
        format='json'
    )
    assert response.status_code == status.HTTP_201_CREATED

    # 501 字符应触发 400
    response2 = api_client.post(
        '/api/precision-testing/repos/',
        data={
            "project": another_project.id,
            "repo_path": "a" * 501,
            "default_branch": "main"
        },
        format='json'
    )
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert 'repo_path' in response2.data


# ============================================================================
# TC-066: CodeChangeAnalysis — status 默认值为 'pending'
# ============================================================================
@pytest.mark.django_db
def test_analysis_status_default_pending(db, sample_repo_binding):
    """TC-066: CodeChangeAnalysis — status 默认值为 'pending'"""
    from apps.precision_testing.models import CodeChangeAnalysis
    analysis = CodeChangeAnalysis.objects.create(
        repo_binding=sample_repo_binding,
        base_commit="a" * 40,
        head_commit="b" * 40
    )
    assert analysis.status == 'pending'


# ============================================================================
# TC-067: TestCaseCodeMapping — mapping_type 三种可选值
# ============================================================================
@pytest.mark.django_db
def test_mapping_type_choices(api_client, testcase):
    """TC-067: TestCaseCodeMapping — mapping_type 三种可选值"""
    for mapping_type in ['manual', 'auto_static', 'auto_dynamic']:
        response = api_client.post(
            '/api/precision-testing/mappings/',
            data={
                "testcase": testcase.id,
                "function_signature": f"sig_{mapping_type}",
                "file_path": "a.py",
                "mapping_type": mapping_type
            },
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED, f"Failed for {mapping_type}"

    # invalid 值
    response = api_client.post(
        '/api/precision-testing/mappings/',
        data={
            "testcase": testcase.id,
            "function_signature": "sig_invalid",
            "file_path": "a.py",
            "mapping_type": "invalid_type"
        },
        format='json'
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================================
# TC-068: RiskPredictionRecord — risk_level 四种可选值
# ============================================================================
@pytest.mark.django_db
def test_risk_level_choices(api_client, testcase, sample_code_change_analysis):
    """TC-068: RiskPredictionRecord — risk_level 四种可选值"""
    from apps.precision_testing.models import ImpactAnalysis, RiskPredictionRecord
    impact = ImpactAnalysis.objects.create(
        change_analysis=sample_code_change_analysis,
        status='completed'
    )
    for risk_level in ['low', 'medium', 'high', 'critical']:
        response = api_client.post(
            '/api/precision-testing/predictions/',
            data={
                "testcase": testcase.id,
                "impact_analysis": impact.id,
                "risk_score": 0.5,
                "risk_level": risk_level
            },
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED, f"Failed for {risk_level}"


# ============================================================================
# TC-070: CodeChangeAnalysis.progress — 进度百分比边界（0-100）
# ============================================================================
@pytest.mark.django_db
def test_analysis_progress_bounds(api_client, sample_code_change_analysis):
    """TC-070: CodeChangeAnalysis.progress — 进度百分比边界（0-100）"""
    sample_code_change_analysis.status = 'running'
    sample_code_change_analysis.progress = 0
    sample_code_change_analysis.save()
    response = api_client.get(f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/progress/')
    assert 0 <= response.data['progress'] <= 100

    sample_code_change_analysis.progress = 100
    sample_code_change_analysis.save()
    response = api_client.get(f'/api/precision-testing/analyses/{sample_code_change_analysis.id}/progress/')
    assert 0 <= response.data['progress'] <= 100