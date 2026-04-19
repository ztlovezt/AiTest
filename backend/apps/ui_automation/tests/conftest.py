# -*- coding: utf-8 -*-
"""
UI 自动化 pytest 配置文件
"""
import sys
import os

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
_project_root = os.path.dirname(_backend_dir)

# 修正 sys.path：移除项目根目录，确保 backend 目录在前面
while _project_root in sys.path:
    sys.path.remove(_project_root)

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# 设置 DJANGO_SETTINGS_MODULE
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'

# 关键修复：只清除 backend 顶层模块的缓存
# 不删除 backend.* 子模块，避免破坏 pytest 的导入链
if 'backend' in sys.modules:
    del sys.modules['backend']

import pytest
import django

# 初始化 Django
django.setup()


def pytest_addoption(parser):
    """添加命令行选项"""
    parser.addoption("--ui-engine", action="store", default="playwright", help="UI测试引擎 (playwright/selenium)")
    parser.addoption("--ui-browser", action="store", default="chrome", help="浏览器类型")
    parser.addoption("--ui-headless", action="store", default="false", help="是否无头模式")


@pytest.fixture(scope="session")
def ui_engine(request):
    """UI测试引擎 fixture"""
    return request.config.getoption("--ui-engine") or os.environ.get('UI_ENGINE', 'playwright')


@pytest.fixture(scope="session")
def ui_browser(request):
    """浏览器类型 fixture"""
    return request.config.getoption("--ui-browser") or os.environ.get('UI_BROWSER', 'chrome')


@pytest.fixture(scope="session")
def ui_headless(request):
    """是否无头模式 fixture"""
    val = request.config.getoption("--ui-headless") or os.environ.get('UI_HEADLESS', 'false')
    return val.lower() in ('true', '1', 'yes')


@pytest.fixture(scope="session")
def test_suite_id():
    """测试套件ID fixture"""
    return os.environ.get('UI_TEST_SUITE_ID')


@pytest.fixture(scope="session")
def execution_id():
    """执行记录ID fixture"""
    return os.environ.get('UI_EXECUTION_ID')


@pytest.fixture(scope="session")
def username():
    """执行用户名 fixture"""
    return os.environ.get('UI_USERNAME', 'unknown')
