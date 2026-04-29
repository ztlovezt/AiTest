# -*- coding: utf-8 -*-
"""
APP测试执行器 - 继承 BaseTestExecutor
复用基类的 Allure 报告生成和 pytest 执行逻辑
"""
import os
import sys
import subprocess
import glob
import json
# import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from django.conf import settings
from django.utils import timezone
from loguru import logger

from apps.common.executors.base_executor import BaseTestExecutor


class AppTestExecutor(BaseTestExecutor):
    """APP测试执行器，继承 BaseTestExecutor，复用报告生成逻辑"""

    MODULE_NAME = 'APP'

    def __init__(self, base_path: Optional[str] = None):
        """
        初始化测试执行器
        
        Args:
            base_path: 基础路径，默认使用 Django BASE_DIR
        """
        super().__init__()
        
        if base_path is None:
            self.base_path = settings.BASE_DIR
        else:
            self.base_path = base_path

        if not os.path.exists(self.base_path):
            raise ValueError(f"测试项目路径不存在: {self.base_path}")

        self._current_process: Optional[subprocess.Popen] = None
        self.execution = None

        logger.info(f"初始化 AppTestExecutor，基础路径: {self.base_path}")

    def _get_allure_results_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_APP_AUTOMATION, settings.ALLURE_RESULTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_report_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_APP_AUTOMATION, settings.ALLURE_REPORTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_single_file_dir(self, execution_id=None) -> str:
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_APP_AUTOMATION, settings.ALLURE_SINGLE_FILE_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_report_url(self, execution_id: int) -> str:
        return f'/api/app-automation-reports/execution_{execution_id}/index.html'

    def _check_ocr_config(self) -> Dict[str, Any]:
        """
        检查 OCR 配置是否有效
        
        Returns:
            包含 valid 和 message 的字典
        """
        try:
            from apps.app_automation.models import AppTestConfig
            
            config = AppTestConfig.objects.first()
            
            if not config:
                return {
                    'valid': False,
                    'message': '请前往设置中心/APP环境配置中配置 OCR 后再使用'
                }
            
            if not config.ocr_engine:
                return {
                    'valid': False,
                    'message': '请前往设置中心/APP环境配置中配置 OCR 后再使用'
                }
            
            if config.ocr_engine == 'tesseract':
                try:
                    import pytesseract
                    pytesseract.get_tesseract_version()
                    logger.info(f"OCR 配置校验通过: Tesseract OCR")
                    return {'valid': True, 'message': 'OK'}
                except Exception as e:
                    logger.warning(f"Tesseract OCR 不可用: {e}")
                    return {
                        'valid': False,
                        'message': f'Tesseract OCR 未正确安装或配置，请检查安装。错误: {str(e)}'
                    }
            
            return {'valid': True, 'message': 'OK'}
            
        except Exception as e:
            logger.error(f"检查 OCR 配置时发生错误: {e}")
            return {
                'valid': False,
                'message': f'检查 OCR 配置时发生错误: {str(e)}'
            }

    def _get_env_info(self) -> Dict[str, str]:
        return {
            'Module': 'APP Automation',
            'Platform': 'TestHub',
        }

    def _get_executor_info(self, execution_id: int) -> Dict[str, Any]:
        return {
            'name': 'TestHub',
            'type': 'TestHub',
            'buildName': f'APP Test - Execution {execution_id}',
            'reportUrl': self._get_report_url(execution_id),
        }

    def execute_suite(
            self,
            test_suite,
            device_id: str = None,
            package_name: str = '',
            user=None,
            execution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行APP测试套件

        Args:
            test_suite: 测试套件实例
            device_id: 设备ID
            package_name: 应用包名
            user: 执行用户
            execution_id: 已存在的执行记录ID

        Returns:
            执行结果字典
        """
        from apps.app_automation.models import AppTestExecution, AppTestSuiteCase, AppDevice

        logger.info(f"[AppTestExecutor] 开始执行套件: {test_suite.name}")

        try:
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            device = None
            if device_id:
                try:
                    device = AppDevice.objects.get(device_id=device_id)
                except AppDevice.DoesNotExist:
                    logger.warning(f"设备不存在: {device_id}")

            if execution_id:
                self.execution = AppTestExecution.objects.get(id=execution_id)
            else:
                self.execution = AppTestExecution.objects.create(
                    test_suite=test_suite,
                    device=device,
                    user=user,
                    status='running',
                    started_at=timezone.now()
                )

            execution_id = self.execution.id
            start_time = datetime.now()

            suite_cases = AppTestSuiteCase.objects.filter(test_suite=test_suite).select_related('test_case')
            if not suite_cases.exists():
                logger.warning(f"测试套件 {test_suite.name} 没有关联的测试用例")
                self.execution.status = 'completed'
                self.execution.result = 'skipped'
                self.execution.finished_at = timezone.now()
                self.execution.save()
                return {
                    'success': True,
                    'execution_id': execution_id,
                    'total_count': 0,
                    'passed_count': 0,
                    'failed_count': 0,
                    'skipped_count': 0,
                }

            total_passed = 0
            total_failed = 0
            total_skipped = 0
            all_test_cases = []

            for suite_case in suite_cases:
                test_case = suite_case.test_case

                case_package = package_name or (test_case.app_package.package_name if test_case.app_package else '')

                case_result = self.run_tests(
                    test_case_id=test_case.id,
                    device_id=device_id,
                    package_name=case_package,
                    execution_id=execution_id,
                    username=user.username if user else 'unknown',
                    generate_report_flag=False
                )

                if case_result.get('success'):
                    total_passed += 1
                else:
                    total_failed += 1

                all_test_cases.append({
                    'test_case_name': test_case.name,
                    'test_case_id': test_case.id,
                    'status': 'passed' if case_result.get('success') else 'failed',
                    'duration': case_result.get('result_data', {}).get('duration', 0),
                    'error': case_result.get('error', ''),
                })

            duration = (datetime.now() - start_time).total_seconds()

            if total_failed == 0 and total_passed > 0:
                status = 'completed'
                result = 'passed'
            elif total_failed > 0 and total_passed == 0:
                status = 'completed'
                result = 'failed'
            elif total_failed > 0 and total_passed > 0:
                status = 'completed'
                result = 'partial_failed'
            else:
                status = 'completed'
                result = 'skipped'

            result_data = {
                'total': total_passed + total_failed + total_skipped,
                'passed': total_passed,
                'failed': total_failed,
                'skipped': total_skipped,
                'duration': duration,
                'test_cases': all_test_cases,
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            self.execution.status = status
            self.execution.result = result
            self.execution.finished_at = timezone.now()
            self.execution.duration = duration
            self.execution.passed_steps = total_passed
            self.execution.failed_steps = total_failed
            self.execution.skipped_steps = total_skipped
            self.execution.total_steps = total_passed + total_failed + total_skipped
            self.execution.result_data = result_data
            self.execution.report_path = self._get_allure_report_dir(execution_id)
            self.execution.report_url = self._get_report_url(execution_id)
            self.execution.save()

            # 生成 Allure 报告
            logger.info(f"[AppTestExecutor] 开始生成报告: execution_{execution_id}")
            try:
                report_success = self.generate_report(execution_id)
                if report_success:
                    logger.info(f"[AppTestExecutor] 报告生成成功: execution_{execution_id}")
                else:
                    logger.warning(f"[AppTestExecutor] 报告生成失败: execution_{execution_id}")
            except Exception as report_error:
                logger.error(f"[AppTestExecutor] 报告生成异常: {report_error}", exc_info=True)

            logger.info(f"[AppTestExecutor] 套件执行完成: {test_suite.name}")

            # 从测试套件直接获取项目名称
            project_name = test_suite.project.name if test_suite.project else ''

            return {
                'success': total_failed == 0,
                'execution_id': execution_id,
                'report_path': self._get_allure_report_dir(execution_id),
                'report_url': self._get_report_url(execution_id),
                'total_count': total_passed + total_failed + total_skipped,
                'passed_count': total_passed,
                'failed_count': total_failed,
                'skipped_count': total_skipped,
                'duration': duration,
                'result_data': result_data,
                'project_name': project_name,
            }

        except Exception as e:
            logger.error(f"[AppTestExecutor] 执行套件失败: {str(e)}", exc_info=True)
            if self.execution:
                self.execution.status = 'error'
                self.execution.error_message = str(e)
                self.execution.finished_at = timezone.now()
                self.execution.save()
            return {
                'success': False,
                'error': str(e),
            }

    def run_tests(
            self,
            test_case_id: int,
            device_id: str,
            package_name: str,
            execution_id: Optional[int] = None,
            username: Optional[str] = None,
            generate_report_flag: bool = True,
    ) -> Dict[str, Any]:
        """
        运行APP测试用例并生成报告
        
        Args:
            test_case_id: 测试用例ID
            device_id: 设备ID
            package_name: 应用包名
            execution_id: 执行记录ID
            username: 执行用户名，用于日志目录分组
            generate_report_flag: 是否生成报告（被execute_suite调用时设为False）
            
        Returns:
            执行结果字典
        """
        logger.info(f"开始执行APP测试: test_case_id={test_case_id}, device={device_id}")

        ocr_check_result = self._check_ocr_config()
        if not ocr_check_result['valid']:
            logger.error(f"OCR 配置校验失败: {ocr_check_result['message']}")
            return {
                'success': False,
                'error': ocr_check_result['message'],
                'result_data': {}
            }

        original_cwd = os.getcwd()
        start_time = datetime.now()
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')

        try:
            os.chdir(self.base_path)

            env = os.environ.copy()
            env['PYTHONPATH'] = self._build_pythonpath()
            env['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
            env['PYTHONUTF8'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            # self._apply_tesseract_runtime_env(env)

            env['APP_TEST_CASE_ID'] = str(test_case_id)
            env['APP_DEVICE_ID'] = str(device_id) if device_id else '1'
            env['APP_PACKAGE_NAME'] = str(package_name) if package_name else ''
            if execution_id:
                env['APP_EXECUTION_ID'] = str(execution_id)
            if username:
                env['APP_USERNAME'] = str(username)

            allure_results_dir = self._get_allure_results_dir(execution_id)
            os.makedirs(allure_results_dir, exist_ok=True)

            # 验证测试目录是否存在
            test_dir = os.path.join(self.base_path, 'apps', 'app_automation', 'tests')
            if not os.path.exists(test_dir):
                logger.error(f"测试目录不存在: {test_dir}")
                return {
                    'success': False,
                    'error': f'测试目录不存在: {test_dir}',
                }

            # 首先验证pytest能否收集测试
            logger.info("验证pytest测试收集...")
            collect_args = [
                sys.executable, '-m', 'pytest',
                'apps/app_automation/tests/',
                '--collect-only',
                '-q',
            ]
            
            collect_result = subprocess.run(
                collect_args,
                cwd=self.base_path,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                timeout=30
            )
            
            logger.info(f"测试收集输出:\n{collect_result.stdout}")
            if collect_result.stderr:
                logger.warning(f"测试收集错误:\n{collect_result.stderr}")
            
            if collect_result.returncode != 0 and 'collected' not in collect_result.stdout:
                logger.error(f"pytest 无法收集测试，退出码: {collect_result.returncode}")
                logger.error(f"stdout: {collect_result.stdout}")
                logger.error(f"stderr: {collect_result.stderr}")
                return {
                    'success': False,
                    'error': f'pytest 无法收集测试。Stdout: {collect_result.stdout[:500]}, Stderr: {collect_result.stderr[:500]}',
                }

            pytest_args = [
                sys.executable, '-m', 'pytest',
                'apps/app_automation/tests/',
                '-s', '-v',
                '--alluredir', allure_results_dir,
                '--tb=long',
                '--capture=no',
            ]

            logger.info(f"执行命令: {' '.join(pytest_args)}")
            logger.info(f"工作目录: {os.getcwd()}")
            logger.info(f"PYTHONPATH: {env['PYTHONPATH']}")
            logger.info(f"测试目录: {test_dir}")
            logger.info(f"环境变量 APP_TEST_CASE_ID: {env.get('APP_TEST_CASE_ID')}")
            logger.info(f"环境变量 APP_DEVICE_ID: {env.get('APP_DEVICE_ID')}")

            process = subprocess.Popen(
                pytest_args,
                cwd=self.base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )

            self._current_process = process

            log_file_path = self._get_log_file_path(username or 'unknown')

            output_lines = []
            important_patterns = ['PASSED', 'FAILED', 'ERROR', 'SKIPPED', 'collected', 'passed', 'failed', 'ImportError', 'ModuleNotFoundError']

            log_file = open(log_file_path, 'a', encoding='utf-8')
            try:
                log_file.write(f"\n{'=' * 80}\n")
                log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                               f"执行记录 ID: {execution_id}, 用例 ID: {test_case_id}, "
                               f"设备: {device_id}\n")
                log_file.write(f"{'=' * 80}\n")

                if process.stdout:
                    for line in process.stdout:
                        line = line.rstrip()
                        if line:
                            output_lines.append(line)
                            log_file.write(line + '\n')
                            logger.debug(f"[pytest] {line}")
                            if any(pattern in line for pattern in important_patterns):
                                logger.info(f"[pytest] {line}")

                log_file.write(f"\n[执行完毕]\n")
            finally:
                log_file.close()

            logger.info(f"执行日志已保存: {log_file_path}")

            exit_code = process.wait()
            self._current_process = None

            logger.info(f"pytest 执行完成，退出码: {exit_code}")
            
            # 如果退出码非零，记录完整输出以便调试
            if exit_code != 0:
                logger.error(f"pytest 执行失败，退出码: {exit_code}")
                full_output = "\n".join(output_lines)
                logger.error(f"\u5b8c\u6574\u8f93\u51fa:\n{full_output}")

            test_results = self._parse_allure_results(allure_results_dir)

            if execution_id and generate_report_flag:
                self.generate_report(execution_id)

            end_time = datetime.now()
            end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

            test_cases = []
            for tr in test_results.get('test_results', []):
                test_cases.append({
                    'test_case_name': tr.get('name', 'Unknown'),
                    'status': tr.get('status', 'unknown'),
                    'duration': tr.get('duration', 0),
                    'error': tr.get('error_message', ''),
                    'start_time': tr.get('start_time', ''),
                    'end_time': tr.get('end_time', ''),
                })

            result_data = {
                'total': test_results.get('total', 0),
                'passed': test_results.get('passed', 0),
                'failed': test_results.get('failed', 0),
                'skipped': test_results.get('skipped', 0),
                'duration': (end_time - start_time).total_seconds(),
                'test_cases': test_cases,
                'start_time': start_time_str,
                'end_time': end_time_str,
            }

            return {
                'success': exit_code == 0,
                'exit_code': exit_code,
                'execution_id': execution_id,
                'report_path': self._get_allure_report_dir(execution_id),
                'test_results': test_results,
                'result_data': result_data,
                'total_count': test_results.get('passed', 0) + test_results.get('failed', 0) + test_results.get('skipped', 0),
                'passed_count': test_results.get('passed', 0),
                'failed_count': test_results.get('failed', 0),
                'skipped_count': test_results.get('skipped', 0),
                'output': '\n'.join(output_lines[-50:]),
                'full_output': '\n'.join(output_lines),
                'start_time': start_time_str,
                'end_time': end_time_str,
                'report_url': self._get_report_url(execution_id) if execution_id else '',
            }

        except subprocess.TimeoutExpired:
            logger.error("pytest 执行超时")
            if self._current_process:
                self._current_process.kill()
                self._current_process = None
            return {
                'success': False,
                'error': 'pytest 执行超时',
            }
        except Exception as e:
            logger.error(f"执行测试失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }
        finally:
            os.chdir(original_cwd)

    def _get_log_file_path(self, username: str) -> str:
        """生成日志文件路径"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(
            str(self.base_path), 'logs', 'app_automation', username
        )
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f'{today}.log')

    def _build_pythonpath(self) -> str:
        """构建 PYTHONPATH 环境变量"""
        python_path_parts = [
            str(self.base_path),
            os.path.join(str(self.base_path), 'apps'),
        ]

        for p in sys.path:
            if p and os.path.exists(str(p)) and str(p) not in python_path_parts:
                p_str = str(p)
                if 'site-packages' in p_str or not p_str.endswith('.exe'):
                    python_path_parts.append(p_str)

        return os.pathsep.join(python_path_parts)

    def _parse_allure_results(self, results_dir: str) -> Dict[str, Any]:
        """解析 Allure 测试结果"""
        try:
            result_files = glob.glob(os.path.join(results_dir, '*-result.json'))

            total = 0
            passed = 0
            failed = 0
            broken = 0
            skipped = 0
            test_results = []

            for result_file in result_files:
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        status = data.get('status', '').lower()
                        total += 1

                        if status == 'passed':
                            passed += 1
                        elif status == 'failed':
                            failed += 1
                        elif status == 'broken':
                            broken += 1
                        elif status == 'skipped':
                            skipped += 1

                        # 从statusDetails获取错误信息
                        error_message = ''
                        status_details = data.get('statusDetails', {})
                        if status_details:
                            error_message = status_details.get('message', '')
                            if not error_message and status_details.get('trace'):
                                # 如果没有消息，提取追溯信息的第一行
                                trace = status_details.get('trace', '')
                                error_message = trace.split('\n')[0] if trace else ''

                        test_results.append({
                            'name': data.get('name', 'Unknown'),
                            'status': status,
                            'duration': data.get('time', {}).get('duration', 0) / 1000 if data.get('time') else 0,
                            'error_message': error_message,
                            'start_time': data.get('time', {}).get('start', 0),
                            'end_time': data.get('time', {}).get('stop', 0),
                        })

                except Exception as e:
                    logger.warning(f"解析结果文件失败: {result_file}, 错误: {e}")

            # 总失败数包括'failed'和'broken'
            total_failed = failed + broken
            
            logger.info(f"测试结果统计: 总数={total}, 通过={passed}, 失败={failed}, 异常={broken}, 跳过={skipped}")

            return {
                'total': total,
                'passed': passed,
                'failed': total_failed,  # 包括failed和broken
                'broken': broken,
                'skipped': skipped,
                'test_results': test_results,
            }

        except Exception as e:
            logger.error(f"解析 Allure 结果失败: {str(e)}", exc_info=True)
            return {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'broken': 0,
                'skipped': 0,
                'test_results': [],
            }

    def calculate_progress(self, execution_id: Optional[int] = None) -> int:
        """计算测试进度"""
        try:
            results_dir = self._get_allure_results_dir(execution_id)

            if not os.path.exists(results_dir):
                return 0

            result_files = glob.glob(os.path.join(results_dir, '*-result.json'))

            if not result_files:
                return 0

            file_count = len(result_files)
            progress = min(file_count * 10, 100)

            return progress

        except Exception as e:
            logger.error(f"计算进度失败: {str(e)}")
            return 0

    def stop(self):
        """停止当前执行的测试"""
        if self._current_process:
            try:
                self._current_process.terminate()
                self._current_process.wait(timeout=settings.TIMEOUTS_PROCESS_WAIT)
                logger.info("测试执行已停止")
            except subprocess.TimeoutExpired:
                self._current_process.kill()
                logger.warning("测试执行被强制终止")
            except Exception as e:
                logger.error(f"停止测试失败: {str(e)}")
            finally:
                self._current_process = None
