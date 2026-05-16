"""
Week 1 测试 fixtures
提供 precision_testing 模块测试所需的公共测试数据
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]  # week1 → testcase → tests → testhub_platform
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# 使用 SQLite 内存数据库运行测试，避免 MySQL 迁移冲突
@pytest.fixture(scope='session')
def django_db_modify_db_settings():
    from django.conf import settings
    if settings.configured:
        settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
            'ATOMIC_REQUESTS': True,
        }


@pytest.fixture
def user(db):
    """测试用户"""
    from apps.users.models import User
    return User.objects.create_user(
        username="test_user",
        email="test@example.com",
        password="TestPass123!",
        first_name="Test",
        last_name="User"
    )


@pytest.fixture
def project(db, user):
    """测试项目"""
    from apps.projects.models import Project
    return Project.objects.create(
        name="Test Project",
        description="For testing",
        status="active",
        owner=user
    )


@pytest.fixture
def testcase(db, project, user):
    """测试用例"""
    from apps.testcases.models import TestCase
    return TestCase.objects.create(
        project=project,
        title="Test Case Title",
        description="Test description",
        expected_result="Expected result",
        priority="medium",
        status="active",
        test_type="functional",
        author=user
    )


@pytest.fixture
def another_project(db, user):
    """另一个 Project 实体（用于避免 unique_together 冲突）"""
    from apps.projects.models import Project
    return Project.objects.create(
        name="Another Test Project",
        description="For testing duplicate binding",
        status="active",
        owner=user
    )


@pytest.fixture
def inactive_repo_binding(db, project):
    """未激活的仓库绑定（用于 is_active=False 测试）"""
    from apps.precision_testing.models import RepoBinding
    return RepoBinding.objects.create(
        project=project,
        repo_path="/var/repos/inactive",
        default_branch="develop",
        is_active=False
    )


@pytest.fixture
def completed_analysis_with_impact(db, sample_repo_binding):
    """已完成的影响分析（含 ImpactAnalysis）"""
    from apps.precision_testing.models import (
        CodeChangeAnalysis, ImpactAnalysis, RiskPredictionRecord
    )
    from apps.testcases.models import TestCase

    analysis = CodeChangeAnalysis.objects.create(
        repo_binding=sample_repo_binding,
        base_commit="a" * 40,
        head_commit="b" * 40,
        status='completed',
        progress=100,
        changed_files=['apps/users/views.py', 'apps/projects/models.py'],
        changed_functions=[
            'apps.users.views:get_user',
            'apps.projects.models:Project.create'
        ]
    )
    impact = ImpactAnalysis.objects.create(
        change_analysis=analysis,
        status='completed',
        impacted_functions=[
            'apps.users.views:get_user',
            'apps.projects.models:Project.create',
            'apps.users.views:UserListView.get'
        ],
        impacted_testcases=[1, 2, 3],
        min_regression_set=[1, 2],
        regression_time_estimate=180
    )
    return {
        'analysis': analysis,
        'impact': impact
    }


@pytest.fixture
def running_analysis(db, sample_repo_binding):
    """正在运行中的分析（用于 progress 轮询测试）"""
    from apps.precision_testing.models import CodeChangeAnalysis
    return CodeChangeAnalysis.objects.create(
        repo_binding=sample_repo_binding,
        base_commit="abc1234" + "0" * 57,
        head_commit="def5678" + "0" * 57,
        status='running',
        progress=67,
        task_id='task_123456'
    )


@pytest.fixture
def failed_analysis(db, sample_repo_binding):
    """失败的分析（用于 error_message 测试）"""
    from apps.precision_testing.models import CodeChangeAnalysis
    return CodeChangeAnalysis.objects.create(
        repo_binding=sample_repo_binding,
        base_commit="abc1234" + "0" * 57,
        head_commit="def5678" + "0" * 57,
        status='failed',
        error_message='Git diff failed: repository not found',
        task_id='task_789012'
    )