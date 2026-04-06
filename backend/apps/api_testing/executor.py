# -*- coding: utf-8 -*-
"""
API测试执行器 - 继承 BaseTestExecutor
使用 pytest 执行 API 测试，与 UI/APP 自动化保持一致

特性：
1. 统一使用 pytest 执行 API 测试
2. 支持 fixture、参数化、依赖等高级特性
3. 统一的 Allure 报告生成
4. 与 UI/APP 自动化执行方式一致
"""
import os
import time
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

from django.conf import settings
from django.utils import timezone
from django.db import connection
from loguru import logger

from apps.common.executors.base_executor import BaseTestExecutor
from .models import (
    ApiRequest, TestSuite, TestExecution, RequestHistory,
    TestSuiteRequest, Environment
)


class ApiTestExecutor(BaseTestExecutor):
    """API测试执行器，继承 BaseTestExecutor，使用 pytest 执行"""
    
    MODULE_NAME = 'API'
    
    def __init__(self, base_path: Optional[str] = None):
        super().__init__(base_path)
        self.results = []

    # ======================== 目录管理（实现抽象方法） ========================

    def _get_allure_results_dir(self, execution_id=None) -> str:
        """获取 Allure 结果目录"""
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_RESULTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_report_dir(self, execution_id=None) -> str:
        """获取 Allure 报告目录"""
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_REPORTS_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_allure_single_file_dir(self, execution_id=None) -> str:
        """获取 Allure single-file 报告目录"""
        base_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_SINGLE_FILE_DIR)
        if execution_id:
            return os.path.join(base_dir, f'execution_{execution_id}')
        return base_dir

    def _get_report_url(self, execution_id: int) -> str:
        """获取报告访问URL"""
        return f'/api/api-testing-reports/execution_{execution_id}/index.html'

    def _get_log_file_path(self, username: str) -> str:
        """生成日志文件路径"""
        today = datetime.now().strftime('%Y-%m-%d')
        log_dir = os.path.join(str(self.base_path), 'logs', 'api_testing', username)
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f'{today}.log')

    # ======================== 环境信息（重写基类方法） ========================

    def _get_env_info(self) -> Dict[str, str]:
        """获取环境信息"""
        return {'Module': 'API Testing'}

    def _get_executor_info(self, execution_id: int) -> Dict[str, Any]:
        """获取执行器信息"""
        return {
            'name': 'TestHub',
            'type': 'TestHub',
            'buildName': 'API Test',
            'reportUrl': self._get_report_url(execution_id),
        }

    # ======================== 执行记录管理 ========================

    def _create_execution_record(self, test_suite=None, user=None, single_request=None):
        """创建测试执行记录"""
        self.execution = TestExecution.objects.create(
            test_suite=test_suite,
            single_request=single_request,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=user
        )
        return self.execution

    def _update_execution_result(self, status, passed=0, failed=0, skipped=0, results=None, error_msg=''):
        """更新执行结果"""
        self.execution.status = status
        self.execution.passed_requests = passed
        self.execution.failed_requests = failed
        self.execution.skipped_requests = skipped
        self.execution.total_requests = passed + failed + skipped
        self.execution.end_time = timezone.now()
        self.execution.results = results or []
        if error_msg:
            self.execution.error_message = error_msg
        self.execution.save()

    # ======================== 套件执行（pytest方式，异步） ========================

    def execute_suite(
        self,
        test_suite: TestSuite,
        environment: Optional[Environment] = None,
        user=None,
        async_report: bool = True,
        execution_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行API测试套件（通过 pytest 子进程）

        Args:
            test_suite: 测试套件实例
            environment: 环境配置
            user: 执行用户
            async_report: 是否异步生成报告（默认True，后台线程生成）
            execution_id: 已存在的执行记录ID（可选）

        Returns:
            执行结果字典（包含 execution_id，供前端轮询）
        """
        logger.info(f"[ApiTestExecutor] 开始执行套件: {test_suite.name} (async_report={async_report})")

        try:
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            if execution_id:
                self.execution = TestExecution.objects.get(id=execution_id)
            else:
                self._create_execution_record(test_suite=test_suite, user=user)

            execution_id = self.execution.id
            start_time = datetime.now()

            original_cwd = os.getcwd()
            os.chdir(self.base_path)

            try:
                env_vars = {
                    'API_TEST_SUITE_ID': str(test_suite.id),
                    'API_EXECUTION_ID': str(execution_id),
                    'API_USERNAME': user.username if user else (self.execution.executed_by.username if self.execution.executed_by else 'unknown'),
                    'API_TIMEOUT': str(getattr(settings, 'TIMEOUTS_API_REQUEST', 30)),
                }

                if environment:
                    env_vars['API_ENVIRONMENT_ID'] = str(environment.id)

                exit_code, results_dir = self._execute_with_pytest(
                    test_dir='apps/api_testing/tests/',
                    env_vars=env_vars,
                    execution_id=execution_id
                )

                test_results = self._parse_allure_results(results_dir)

                passed = test_results['passed']
                failed = test_results['failed']
                skipped = test_results.get('skipped', 0)
                duration = (datetime.now() - start_time).total_seconds()

                self.results = []
                for tr in test_results['test_results']:
                    self.results.append({
                        'name': tr['name'],
                        'status': tr['status'],
                        'passed': tr['status'] == 'passed',
                        'skipped': tr['status'] == 'skipped',
                        'error': tr.get('error_message', ''),
                        'duration': tr.get('duration', 0),
                        'response_time': tr.get('response_time', tr.get('duration', 0)),
                        'method': tr.get('method', ''),
                        'url': tr.get('url', ''),
                        'status_code': tr.get('status_code', ''),
                    })

                if failed == 0 and passed > 0:
                    status = 'COMPLETED'
                elif failed > 0 and passed == 0:
                    status = 'FAILED'
                elif failed > 0 and passed > 0:
                    status = 'PARTIAL_FAILED'
                else:
                    status = 'ABORTED'
                self._update_execution_result(status, passed, failed, skipped, self.results)

                if async_report:
                    # 后台线程生成 Allure 报告，不阻塞响应
                    thread = threading.Thread(
                        target=self._async_generate_report,
                        args=(execution_id,),
                        daemon=True
                    )
                    thread.start()
                    logger.info(f"[ApiTestExecutor] 报告生成已提交到后台线程: execution_{execution_id}")
                else:
                    self.generate_report(execution_id)

                end_time = datetime.now()

                return {
                    'success': exit_code == 0,
                    'exit_code': exit_code,
                    'execution_id': execution_id,
                    'total_requests': passed + failed,
                    'passed_count': passed,
                    'failed_count': failed,
                    'duration': duration,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'results': self.results,
                    'report_url': self._get_report_url(execution_id),
                }

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            logger.error(f"[ApiTestExecutor] 套件执行失败: {str(e)}", exc_info=True)
            if self.execution:
                self._update_execution_result('FAILED', error_msg=str(e))
                return {
                    'success': False,
                    'execution_id': self.execution.id,
                    'error': str(e)
                }
            return {'success': False, 'error': str(e)}
        finally:
            connection.close()

    def _async_generate_report(self, execution_id: int):
        """后台线程生成 Allure 报告

        在独立线程中执行，需要自己管理数据库连接。
        """
        try:
            # 关闭可能继承的父进程数据库连接，让 Django 创建新连接
            connection.close()

            # 先更新 report_status 为 GENERATING
            try:
                TestExecution.objects.filter(id=execution_id).update(report_status='GENERATING')
            except Exception:
                pass

            executor = ApiTestExecutor()
            success = executor.generate_report(execution_id)

            # generate_report 内部因 self.execution 为 None 不会更新 report_status，
            # 所以这里直接通过数据库更新
            if success:
                TestExecution.objects.filter(id=execution_id).update(
                    report_status='SUCCESS',
                    report_url=executor._get_report_url(execution_id)
                )
            else:
                TestExecution.objects.filter(id=execution_id).update(report_status='FAILED')

            logger.info(f"[ApiTestExecutor] 后台报告生成完成: execution_{execution_id}, success={success}")
        except Exception as e:
            logger.error(f"[ApiTestExecutor] 后台报告生成失败: execution_{execution_id}, error: {str(e)}", exc_info=True)
            try:
                TestExecution.objects.filter(id=execution_id).update(report_status='FAILED')
            except Exception:
                pass
        finally:
            connection.close()

    # ======================== 单个请求执行（pytest方式） ========================

    def execute_request(
        self,
        api_request: ApiRequest,
        environment: Optional[Environment] = None,
        user=None,
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """
        执行单个API请求（通过 pytest 子进程，生成 Allure 报告）
        
        Args:
            api_request: API请求实例
            environment: 环境配置
            user: 执行用户
            generate_report: 是否生成Allure报告
            
        Returns:
            执行结果字典
        """
        logger.info(f"[ApiTestExecutor] 开始执行单个请求: {api_request.name}")
        
        try:
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
            
            self._create_execution_record(test_suite=None, user=user, single_request=api_request)
            
            execution_id = self.execution.id
            start_time = datetime.now()
            
            original_cwd = os.getcwd()
            os.chdir(self.base_path)
            
            try:
                env_vars = {
                    'API_REQUEST_ID': str(api_request.id),
                    'API_EXECUTION_ID': str(execution_id),
                    'API_USERNAME': user.username if user else 'unknown',
                    'API_TIMEOUT': str(getattr(settings, 'TIMEOUTS_API_REQUEST', 30)),
                    'API_SINGLE_CASE': 'true',
                }
                
                if environment:
                    env_vars['API_ENVIRONMENT_ID'] = str(environment.id)
                
                exit_code, results_dir = self._execute_with_pytest(
                    test_dir='apps/api_testing/tests/',
                    env_vars=env_vars,
                    execution_id=execution_id,
                    extra_args=['-k', 'test_api_single_request']
                )
                
                test_results = self._parse_allure_results(results_dir)
                
                passed = test_results['passed']
                failed = test_results['failed']
                skipped = test_results.get('skipped', 0)
                duration = (datetime.now() - start_time).total_seconds()
                
                status = 'COMPLETED' if failed == 0 else 'FAILED'
                self._update_execution_result(status, passed, failed, skipped)
                
                if generate_report:
                    self.generate_report(execution_id)
                
                end_time = datetime.now()
                
                result_data = {
                    'success': exit_code == 0,
                    'exit_code': exit_code,
                    'execution_id': execution_id,
                    'status': status,
                    'duration': duration,
                    'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'report_url': self._get_report_url(execution_id) if generate_report else None,
                }
                
                if test_results['test_results']:
                    tr = test_results['test_results'][0]
                    result_data['name'] = api_request.name
                    result_data['method'] = api_request.method
                    result_data['error_message'] = tr.get('error_message', '')
                
                return result_data
                
            finally:
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"[ApiTestExecutor] 单个请求执行失败: {str(e)}", exc_info=True)
            if self.execution:
                self._update_execution_result('FAILED', error_msg=str(e))
                return {
                    'success': False,
                    'execution_id': self.execution.id,
                    'error': str(e)
                }
            return {'success': False, 'error': str(e)}
        finally:
            connection.close()

    # ======================== 兼容旧接口（直接执行，不生成报告） ========================

    def execute_request_direct(
        self,
        api_request: ApiRequest,
        environment: Optional[Environment] = None,
        user=None
    ) -> Dict[str, Any]:
        """
        直接执行API请求（不通过pytest，用于快速调试）
        
        注意：此方法不生成Allure报告，仅用于快速验证
        
        Args:
            api_request: API请求实例
            environment: 环境配置
            user: 执行用户
            
        Returns:
            执行结果字典
        """
        from .variable_resolver import VariableResolver
        import requests
        
        logger.info(f"[ApiTestExecutor] 直接执行请求（调试模式）: {api_request.name}")
        
        start_time = time.time()
        
        try:
            resolver = VariableResolver()
            
            variables = {}
            if environment and environment.variables:
                for key, val in environment.variables.items():
                    if isinstance(val, dict) and 'currentValue' in val:
                        variables[key] = val['currentValue']
                    else:
                        variables[key] = val
            
            url = self._replace_variables(api_request.url, variables)
            url = resolver.resolve(url)
            
            headers = {}
            if isinstance(api_request.headers, list):
                for header_item in api_request.headers:
                    if header_item.get('enabled', True) and header_item.get('key'):
                        key = header_item['key']
                        value = self._replace_variables(str(header_item.get('value', '')), variables)
                        value = resolver.resolve(value)
                        headers[key] = value
            elif api_request.headers:
                headers = api_request.headers.copy()
                for key, value in headers.items():
                    headers[key] = self._replace_variables(str(value), variables)
                    headers[key] = resolver.resolve(headers[key])
            
            params = api_request.params.copy() if api_request.params else {}
            for key, value in params.items():
                params[key] = self._replace_variables(str(value), variables)
                params[key] = resolver.resolve(params[key])
            
            body_data = None
            body_kwarg = 'json'  # requests.request 的参数名: json / data / files
            if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
                body_type = api_request.body.get('type', '')
                raw_body = api_request.body.get('raw', '')

                if body_type == 'json':
                    body_data = api_request.body.get('data', {})
                    body_data = self._replace_variables_in_dict(body_data, variables)
                    body_data = self._resolve_variables_in_dict(body_data, resolver)
                    body_kwarg = 'json'

                elif body_type == 'x-www-form-urlencoded':
                    # 表单编码: 将 data 数组转为 dict，然后做变量替换
                    form_data = {}
                    for item in (api_request.body.get('data') or []):
                        if not item.get('enabled', True) or not item.get('key'):
                            continue
                        key = item['key']
                        value = str(item.get('value', ''))
                        value = self._replace_variables(value, variables)
                        value = resolver.resolve(value)
                        form_data[key] = value
                    body_data = form_data
                    body_kwarg = 'data'

                elif body_type == 'form-data':
                    # multipart/form-data
                    form_data = []
                    for item in (api_request.body.get('data') or []):
                        if not item.get('enabled', True) or not item.get('key'):
                            continue
                        key = item['key']
                        value = self._replace_variables(str(item.get('value', '')), variables)
                        value = resolver.resolve(value)
                        form_data.append((key, (item.get('filename', ''), value, item.get('content_type', '')) if item.get('type') == 'file' else (key, value)))
                    body_data = form_data
                    body_kwarg = 'files' if any(item.get('type') == 'file' for item in (api_request.body.get('data') or [])) else 'data'

                elif body_type == 'raw':
                    # 原始文本/XML 等
                    body_data = self._replace_variables(raw_body, variables) if isinstance(raw_body, str) else raw_body
                    body_data = resolver.resolve(body_data) if isinstance(body_data, str) else body_data
                    body_kwarg = 'data'

                elif body_type == 'binary':
                    # 二进制数据（如上传文件）
                    pass  # body_data 保持 None，前端一般不通过这种方式发送

                elif body_type == 'none' or not body_type:
                    body_data = None

            response_kwargs = {
                'method': api_request.method,
                'url': url,
                'headers': headers,
                'params': params,
                'timeout': getattr(settings, 'TIMEOUTS_API_REQUEST', 30),
            }
            if body_data is not None:
                response_kwargs[body_kwarg] = body_data

            response = requests.request(**response_kwargs)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            response_data = {
                'headers': dict(response.headers),
                'body': response.text,
            }
            try:
                json_data = response.json()
                response_data['json'] = json_data
            except (ValueError, requests.exceptions.JSONDecodeError):
                response_data['json'] = None

            history = RequestHistory.objects.create(
                request=api_request,
                environment=environment,
                request_data={
                    'url': url,
                    'method': api_request.method,
                    'headers': headers,
                    'params': params,
                    'body': body_data
                },
                response_data=response_data,
                status_code=response.status_code,
                response_time=response_time,
                executed_by=user
            )
            
            # 执行断言验证
            assertions_results = None
            if api_request.assertions:
                from .utils import execute_assertions
                # 为响应时间断言注入实际耗时
                assertions = list(api_request.assertions)  # 拷贝一份避免修改原数据
                for assertion in assertions:
                    if assertion.get('type') == 'response_time':
                        assertion['actual_time'] = response_time
                assertions_results = execute_assertions(response, assertions)
                # 更新历史记录中的断言结果
                history.assertions_results = assertions_results
                history.save(update_fields=['assertions_results'])
            
            # 执行变量提取
            extracted_variables = {}
            if api_request.extract_variables:
                from .tests.test_api_flow import VariableExtractor
                extracted_variables = VariableExtractor.extract_from_response(
                    response, api_request.extract_variables
                )
                if extracted_variables:
                    logger.info(f"[ApiTestExecutor] 提取变量: {list(extracted_variables.keys())}")
            
            return {
                'success': True,
                'history_id': history.id,
                'status_code': response.status_code,
                'response_time': response_time,
                'response_data': response_data,
                'assertions_results': assertions_results,
                'extracted_variables': extracted_variables,
                'name': api_request.name,
                'method': api_request.method,
                'url': url,
            }
            
        except Exception as e:
            logger.error(f"[ApiTestExecutor] 请求执行失败: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'name': api_request.name,
                'method': api_request.method,
                'url': api_request.url,
            }

    # ======================== 辅助方法 ========================

    def _replace_variables(self, text: str, variables: Dict) -> str:
        """替换文本中的变量"""
        if not isinstance(text, str):
            return text
        
        result = text
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result

    def _replace_variables_in_dict(self, data, variables: Dict):
        """递归替换字典中的变量"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        else:
            return data

    def _resolve_variables_in_dict(self, data, resolver):
        """递归解析字典中的动态函数占位符"""
        if isinstance(data, dict):
            return {k: self._resolve_variables_in_dict(v, resolver) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_variables_in_dict(item, resolver) for item in data]
        elif isinstance(data, str):
            return resolver.resolve(data)
        else:
            return data
