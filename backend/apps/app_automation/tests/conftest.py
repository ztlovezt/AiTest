# -*- coding: utf-8 -*-
"""
pytest 配置文件
"""
import sys
import os
import pytest

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

import django

django.setup()


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption("--device-id", action="store", default=None, help="设备ID")
    parser.addoption("--package-name", action="store", default=None, help="应用包名")


@pytest.fixture(scope="session")
def device_id(request):
    """设备ID fixture"""
    return request.config.getoption("--device-id") or os.environ.get('APP_DEVICE_ID')


@pytest.fixture(scope="session")
def package_name(request):
    """应用包名 fixture"""
    return request.config.getoption("--package-name") or os.environ.get('APP_PACKAGE_NAME')


@pytest.fixture(scope="session")
def test_case_id():
    """测试用例ID fixture"""
    return os.environ.get('APP_TEST_CASE_ID')


@pytest.fixture(scope="session")
def execution_id():
    """执行记录ID fixture"""
    return os.environ.get('APP_EXECUTION_ID')


@pytest.fixture(scope="session")
def username():
    """用户名 fixture"""
    return os.environ.get('APP_USERNAME', 'unknown')
