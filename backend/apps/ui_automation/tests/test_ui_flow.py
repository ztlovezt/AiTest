# -*- coding: utf-8 -*-
"""
UI 自动化测试 - pytest 入口
通过环境变量接收参数，使用 allure 记录测试步骤
"""
import logging
import pytest
import allure
import json
import os

from apps.ui_automation.models import (
    TestSuite, TestCase, TestCaseExecution, TestExecution
)
from apps.ui_automation.ui_flow_runner import UiFlowRunner

logger = logging.getLogger(__name__)

_test_suite_cache = {}
_test_cases_cache = {}


def _make_progress_callback(execution_id):
    """创建进度回调函数"""
    if not execution_id:
        return None

    def callback(current_step, total_steps, step_name, status):
        if total_steps <= 0 or status == 'running':
            return
        progress = int(10 + (current_step / total_steps) * 80)
        progress = min(progress, 90)
        try:
            TestExecution.objects.filter(id=execution_id).update(progress=progress)
        except Exception as e:
            logger.debug(f"更新执行进度失败: {e}")

        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            channel_layer = get_channel_layer()
            if channel_layer:
                async_to_sync(channel_layer.group_send)(
                    f"ui_execution_{execution_id}",
                    {
                        "type": "execution_update",
                        "execution_id": int(execution_id),
                        "status": "running",
                        "progress": progress,
                        "message": f"步骤 {current_step}/{total_steps}: {step_name}",
                    }
                )
        except Exception:
            pass

    return callback


def _get_test_cases_data(test_suite_id):
    """预先获取测试套件中所有用例和步骤数据（带缓存）"""
    test_suite_id = str(test_suite_id)

    if test_suite_id in _test_suite_cache:
        return _test_suite_cache[test_suite_id], _test_cases_cache.get(test_suite_id, [])

    test_suite = TestSuite.objects.get(id=test_suite_id)
    suite_test_cases = test_suite.suite_test_cases.filter(
        enabled=True
    ).select_related('test_case').order_by('order')
    test_cases = []

    for stc in suite_test_cases:
        test_case = stc.test_case
        case_data = {
            'id': test_case.id,
            'name': test_case.name,
            'project_id': test_suite.project.id,
            'steps': []
        }

        steps = test_case.steps.select_related('element', 'element__locator_strategy').order_by('step_number')
        for step in steps:
            step_data = {
                'id': step.id,
                'step_number': step.step_number,
                'action_type': step.action_type,
                'description': step.description,
                'input_value': step.input_value,
                'wait_time': step.wait_time,
                'assert_type': step.assert_type,
                'assert_value': step.assert_value,
                'element': None
            }
            if step.element:
                step_data['element'] = {
                    'id': step.element.id,
                    'name': step.element.name,
                    'locator_value': step.element.locator_value,
                    'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css'
                }
            case_data['steps'].append(step_data)

        test_cases.append(case_data)

    _test_suite_cache[test_suite_id] = test_suite
    _test_cases_cache[test_suite_id] = test_cases

    return test_suite, test_cases


def pytest_generate_tests(metafunc):
    """动态生成测试用例参数"""
    if 'case_index' in metafunc.fixturenames:
        test_suite_id = os.environ.get('UI_TEST_SUITE_ID')
        if test_suite_id:
            try:
                _, test_cases = _get_test_cases_data(test_suite_id)
                case_ids = [f"case_{i}_{tc['id']}_{tc['name'][:20]}" for i, tc in enumerate(test_cases)]
                metafunc.parametrize('case_index', list(range(len(test_cases))), ids=case_ids)
            except Exception as e:
                logger.error(f"获取测试用例失败: {e}")
                metafunc.parametrize('case_index', [])


@pytest.fixture(scope="session")
def suite_data(test_suite_id):
    """获取测试套件数据（session 级别，只查询一次）"""
    if not test_suite_id:
        return None
    test_suite, _ = _get_test_cases_data(test_suite_id)
    return test_suite


@pytest.fixture(scope="session")
def all_test_cases(test_suite_id):
    """获取所有测试用例数据（session 级别，只查询一次）"""
    if not test_suite_id:
        return []
    _, test_cases = _get_test_cases_data(test_suite_id)
    return test_cases


@pytest.fixture(scope="function")
def case_data(case_index, all_test_cases):
    """获取当前测试用例数据"""
    if case_index < len(all_test_cases):
        return all_test_cases[case_index]
    return None


@allure.feature("UI自动化测试")
def test_ui_automation(case_index, case_data, suite_data, execution_id, ui_engine, ui_browser, ui_headless, username):
    """UI 自动化测试主入口"""
    if not case_data:
        pytest.skip("无测试用例数据")

    test_case_id = case_data['id']
    test_case_name = case_data['name']

    allure.dynamic.title(f"用例: {test_case_name}")
    allure.dynamic.suite(suite_data.name if suite_data else "UI自动化测试")

    # 写入引擎/浏览器/执行模式标签，显示在 Allure 报告的测试步骤和执行环境中
    engine_display = {'playwright': 'Playwright', 'selenium': 'Selenium'}.get(ui_engine, ui_engine)
    browser_display = {
        'chrome': 'Chrome', 'firefox': 'Firefox', 'edge': 'Edge', 'safari': 'Safari'
    }.get(ui_browser, ui_browser)
    mode_display = 'Headless' if ui_headless else 'Headed'

    allure.dynamic.label('engine', engine_display)
    allure.dynamic.label('browser', browser_display)
    allure.dynamic.label('execution_mode', mode_display)

    runner = UiFlowRunner(engine=ui_engine, browser=ui_browser, headless=ui_headless)
    base_url = suite_data.project.base_url if suite_data and suite_data.project else ''

    with allure.step(f"启动浏览器 ({browser_display}, {mode_display})"):
        allure.attach(
            f"引擎: {engine_display}\n浏览器: {browser_display}\n执行模式: {mode_display}\n基础URL: {base_url}",
            name="执行环境",
            attachment_type=allure.attachment_type.TEXT
        )

    result = runner.run_test_case(case_data, base_url=base_url)

    for step_result in result.get('steps', []):
        step_desc = step_result.get('description', step_result.get('action_type', 'Unknown'))
        status = 'passed' if step_result.get('success') else 'failed'
        with allure.step(f"[{step_result.get('action_type', '')}] {step_desc}"):
            if step_result.get('error'):
                allure.attach(step_result['error'], name="错误信息", attachment_type=allure.attachment_type.TEXT)
            if step_result.get('result'):
                allure.attach(str(step_result['result']), name="获取文本", attachment_type=allure.attachment_type.TEXT)

    for screenshot in result.get('screenshots', []):
        if screenshot.get('url') and screenshot['url'].startswith('data:image'):
            import base64
            try:
                img_data = base64.b64decode(screenshot['url'].split(',')[1])
                allure.attach(img_data, name=screenshot.get('description', '截图'), attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass

    if result.get('error'):
        allure.attach(result['error'], name="用例错误", attachment_type=allure.attachment_type.TEXT)

    assert result['status'] == 'passed', f"用例执行失败: {result.get('error', '未知错误')}"

    allure.attach(
        f"用例: {test_case_name}\n状态: {result['status']}\n步骤数: {len(result.get('steps', []))}",
        name="执行统计",
        attachment_type=allure.attachment_type.TEXT
    )
