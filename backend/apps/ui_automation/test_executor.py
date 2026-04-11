# -*- coding: utf-8 -*-
"""
UI自动化测试执行器 - 继承 BaseTestExecutor
使用 pytest 执行 UI 测试，与 API/APP 自动化保持一致
"""
import os
import sys
import subprocess
import threading
from datetime import datetime
from typing import Optional, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.db import connection
from loguru import logger

from apps.common.executors.base_executor import BaseTestExecutor
from .models import (
    TestExecution, TestCaseExecution, TestSuite, TestCase, TestSuiteTestCase
)


class UITestExecutor(BaseTestExecutor):
    """UI测试执行器，继承 BaseTestExecutor，使用 pytest 执行"""
    
    MODULE_NAME = 'UI'
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)

    def _get_allure_results_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_UI_AUTOMATION, settings.ALLURE_RESULTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_report_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_UI_AUTOMATION, settings.ALLURE_REPORTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_single_file_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_UI_AUTOMATION, settings.ALLURE_SINGLE_FILE_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_report_url(self, execution_id: int) -> str:
        return f'/api/ui-testing-reports/execution_{execution_id}/index.html'

    def _get_env_info(self) -> Dict[str, str]:
        return {
            'Module': 'UI Automation',
            'Platform': 'TestHub',
        }

    def _get_executor_info(self, execution_id: int) -> Dict[str, Any]:
        return {
            'name': 'TestHub',
            'type': 'TestHub',
            'buildName': f'UI Test - Execution {execution_id}',
            'reportUrl': self._get_report_url(execution_id),
        }

    def execute_suite(
        self,
        test_suite: TestSuite,
        engine: str = 'playwright',
        browser: str = 'chrome',
        headless: bool = False,
        user=None,
        async_report: bool = True,
        execution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行UI测试套件（通过 pytest 子进程）

        Args:
            test_suite: 测试套件实例
            engine: 执行引擎 (playwright/selenium)
            browser: 浏览器类型 (chrome/firefox/safari/edge).
            headless: 是否无头模式
            user: 执行用户.
            async_report: 是否异步生成报告.
            execution_id: 已存在的执行记录ID.

        Returns:
            执行结果字典
        """
        logger.info(f"[UITestExecutor] 开始执行套件: {test_suite.name}")

        try:
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            if execution_id:
                self.execution = TestExecution.objects.get(id=execution_id)
            else:
                self.execution = TestExecution.objects.create(
                    project=test_suite.project,
                    test_suite=test_suite,
                    status='RUNNING',
                    engine=engine,
                    browser=browser,
                    headless=headless,
                    executed_by=user,
                    started_at=timezone.now()
                )

            execution_id = self.execution.id
            start_time = datetime.now()

            original_cwd = os.getcwd()
            os.chdir(self.base_path)

            try:
                env_vars = {
                    'UI_TEST_SUITE_ID': str(test_suite.id),
                    'UI_EXECUTION_ID': str(execution_id),
                    'UI_USERNAME': user.username if user else 'unknown',
                    'UI_ENGINE': engine,
                    'UI_BROWSER': browser,
                    'UI_HEADLESS': str(headless).lower(),
                }

                exit_code, results_dir = self._execute_with_pytest(
                    test_dir='apps/ui_automation/tests/',
                    env_vars=env_vars,
                    execution_id=execution_id
                )

                test_results = self._parse_allure_results(results_dir)

                passed = test_results['passed']
                failed = test_results['failed']
                duration = (datetime.now() - start_time).total_seconds()

                # 转换测试结果格式，适配前端显示
                test_cases = []
                for tr in test_results.get('test_results', []):
                    test_cases.append({
                        'test_case_name': tr.get('name', 'Unknown'),
                        'test_case_id': tr.get('id', ''),
                        'status': tr.get('status', 'unknown'),
                        'duration': tr.get('duration', 0),
                        'error': tr.get('error_message', ''),
                        'steps': tr.get('steps', []),
                        'start_time': tr.get('start_time', ''),
                        'end_time': tr.get('end_time', ''),
                    })

                if failed == 0 and passed > 0:
                    status = 'PASSED'
                elif failed > 0 and passed == 0:
                    status = 'FAILED'
                elif failed > 0 and passed > 0:
                    status = 'PARTIAL_FAILED'
                else:
                    status = 'ABORTED'

                result_data = {
                    'total': passed + failed,
                    'passed': passed,
                    'failed': failed,
                    'skipped': test_results.get('skipped', 0),
                    'duration': duration,
                    'test_cases': test_cases,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }

                self.execution.status = status
                self.execution.finished_at = timezone.now()
                self.execution.duration = duration
                self.execution.passed_cases = passed
                self.execution.failed_cases = failed
                self.execution.skipped_cases = test_results.get('skipped', 0)
                self.execution.total_cases = passed + failed + test_results.get('skipped', 0)
                self.execution.result_data = result_data
                self.execution.save()

                if async_report:
                    thread = threading.Thread(
                        target=self._async_generate_report,
                        args=(execution_id,),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"[UITestExecutor] 报告生成已提交到后台线程: execution_{execution_id}")
                else:
                    self.generate_report(execution_id)

                end_time = datetime.now()

                # 从测试套件直接获取项目名称
                project_name = test_suite.project.name if test_suite.project else ''

                return {
                    'success': exit_code == 0,
                    'exit_code': exit_code,
                    'execution_id': execution_id,
                    'total_count': passed + failed,
                    'passed_count': passed,
                    'failed_count': failed,
                    'skipped_count': test_results.get('skipped', 0),
                    'duration': duration,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'report_url': self._get_report_url(execution_id),
                    'project_name': project_name,
                }

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            logger.error(f"[UITestExecutor] 套件执行失败: {str(e)}", exc_info=True)
            if self.execution:
                self.execution.status = 'FAILED'
                self.execution.finished_at = timezone.now()
                self.execution.save()
                return {
                    'success': False,
                    'execution_id': self.execution.id,
                    'error': str(e)
                }
            return {'success': False, 'error': str(e)}
        finally:
            connection.close()

    def _async_generate_report(self, execution_id: int):
        """后台线程生成 Allure 报告"""
        try:
            self.generate_report(execution_id)
            logger.info(f"[UITestExecutor] 报告生成完成: execution_{execution_id}")
        except Exception as e:
            logger.error(f"[UITestExecutor] 报告生成失败: {e}")

    def stop(self):
        """停止当前执行的测试"""
        super().stop()


class TestExecutor(UITestExecutor):
    """兼容旧版本的执行器类名"""
    pass
