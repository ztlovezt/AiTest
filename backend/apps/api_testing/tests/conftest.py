# -*- coding: utf-8 -*-
"""
API 自动化测试 - pytest 配置文件
"""
import sys
import os

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
_project_root = os.path.dirname(_backend_dir)

while _project_root in sys.path:
    sys.path.remove(_project_root)

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

if 'backend' in sys.modules:
    del sys.modules['backend']

import pytest
import django

django.setup()


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption("--api-timeout", action="store", default="30", help="API请求超时时间(秒)")


@pytest.fixture(scope="session")
def api_test_suite_id():
    """测试套件ID fixture"""
    return os.environ.get('API_TEST_SUITE_ID')


@pytest.fixture(scope="session")
def api_request_id():
    """单个请求ID fixture"""
    return os.environ.get('API_REQUEST_ID')


@pytest.fixture(scope="session")
def api_execution_id():
    """执行记录ID fixture"""
    return os.environ.get('API_EXECUTION_ID')


@pytest.fixture(scope="session")
def api_environment_id():
    """环境ID fixture"""
    return os.environ.get('API_ENVIRONMENT_ID')


@pytest.fixture(scope="session")
def api_username():
    """执行用户名 fixture"""
    return os.environ.get('API_USERNAME', 'unknown')


@pytest.fixture(scope="session")
def api_timeout(request):
    """API请求超时时间 fixture"""
    return int(request.config.getoption("--api-timeout") or os.environ.get('API_TIMEOUT', '30'))


@pytest.fixture(scope="session")
def api_single_case():
    """是否单个用例执行 fixture"""
    return os.environ.get('API_SINGLE_CASE', 'false').lower() in ('true', '1', 'yes')


def pytest_configure(config):
    """根据环境变量动态配置 pytest 收集行为

    当执行测试套件时（API_TEST_SUITE_ID 存在），排除 test_api_single_request；
    当执行单个请求时（API_SINGLE_CASE=true），排除 test_api_request。
    避免同文件中的两个测试入口互相干扰。
    """
    import warnings

    suite_id = os.environ.get('API_TEST_SUITE_ID')
    single_case = os.environ.get('API_SINGLE_CASE', 'false').lower() in ('true', '1', 'yes')

    if suite_id and not single_case:
        # 套件执行：只收集 test_api_request
        config.addinivalue_line('filterwarnings', 'ignore::pytest.PytestUnknownMarkWarning')
        setattr(config, '_testhub_collect_pattern', 'test_api_request and not test_api_single_request')
    elif single_case:
        # 单个请求执行：只收集 test_api_single_request（由 -k 参数控制，这里不需要额外处理）
        pass


def pytest_collection_modifyitems(session, config, items):
    """在测试收集完成后，根据环境变量过滤掉不需要的测试项

    套件执行时移除 test_api_single_request，避免它被 pytest 收集后
    因缺少 API_REQUEST_ID 而被 skip，但仍写入 Allure results 导致结果中出现多余用例。
    """
    suite_id = os.environ.get('API_TEST_SUITE_ID')
    single_case = os.environ.get('API_SINGLE_CASE', 'false').lower() in ('true', '1', 'yes')

    if suite_id and not single_case:
        # 套件执行模式：移除 test_api_single_request 相关的测试项
        items[:] = [item for item in items if item.name != 'test_api_single_request']
