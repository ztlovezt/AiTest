# -*- coding: utf-8 -*-
"""
API 自动化测试 - pytest 入口
通过环境变量接收参数，使用 allure 记录测试步骤

支持功能：
1. 前置/后置脚本执行
2. 变量提取和传递
3. 条件执行
4. 断言验证
5. Allure报告生成
"""
import logging
import pytest
import allure
import json
import os
import re
import time
import requests
from typing import Dict, Any, List, Optional

from apps.api_testing.models import (
    ApiRequest, TestSuite, TestExecution, RequestHistory,
    TestSuiteRequest, Environment
)
from apps.api_testing.variable_resolver import VariableResolver

logger = logging.getLogger(__name__)

_suite_cache = {}
_requests_cache = {}
_environment_cache = {}
_session_variables = {}


class ScriptExecutor:
    """脚本执行器 - 支持前置/后置脚本执行"""
    
    @staticmethod
    def execute_pre_request(script: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行前置脚本
        
        Args:
            script: 脚本内容
            context: 执行上下文，包含 variables, environment 等
            
        Returns:
            执行结果，包含更新后的变量
        """
        if not script or not script.strip():
            return {'success': True, 'variables': {}, 'logs': []}
        
        result = {
            'success': True,
            'variables': {},
            'logs': [],
            'error': None
        }
        
        local_vars = {
            'variables': context.get('variables', {}),
            'environment': context.get('environment', {}),
            'request': context.get('request', {}),
            'set_variable': lambda k, v: result['variables'].__setitem__(k, v),
            'log': lambda msg: result['logs'].append(str(msg)),
        }
        
        try:
            exec(script, {'__builtins__': __builtins__}, local_vars)
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            result['logs'].append(f"脚本执行错误: {str(e)}")
        
        return result
    
    @staticmethod
    def execute_post_request(script: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行后置脚本
        
        Args:
            script: 脚本内容
            context: 执行上下文，包含 variables, response 等
            
        Returns:
            执行结果，包含提取的变量
        """
        if not script or not script.strip():
            return {'success': True, 'variables': {}, 'logs': []}
        
        result = {
            'success': True,
            'variables': {},
            'logs': [],
            'error': None
        }
        
        local_vars = {
            'variables': context.get('variables', {}),
            'response': context.get('response', {}),
            'response_json': context.get('response_json'),
            'status_code': context.get('status_code'),
            'response_time': context.get('response_time'),
            'request': context.get('request', {}),
            'set_variable': lambda k, v: result['variables'].__setitem__(k, v),
            'log': lambda msg: result['logs'].append(str(msg)),
            'json_path': ScriptExecutor._json_path_extractor,
            'regex_extract': ScriptExecutor._regex_extractor,
        }
        
        try:
            exec(script, {'__builtins__': __builtins__}, local_vars)
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            result['logs'].append(f"脚本执行错误: {str(e)}")
        
        return result
    
    @staticmethod
    def _json_path_extractor(data: Any, path: str) -> Optional[Any]:
        """JSONPath提取器"""
        try:
            from jsonpath_ng import parse
            matches = parse(path).find(data)
            return matches[0].value if matches else None
        except Exception:
            return None
    
    @staticmethod
    def _regex_extractor(text: str, pattern: str, group: int = 0) -> Optional[str]:
        """正则提取器"""
        try:
            match = re.search(pattern, text)
            return match.group(group) if match else None
        except Exception:
            return None


class VariableExtractor:
    """变量提取器 - 从响应中提取变量"""
    
    @staticmethod
    def extract_from_response(response: requests.Response, extraction_rules: List[Dict]) -> Dict[str, Any]:
        """
        从响应中提取变量
        
        Args:
            response: HTTP响应对象
            extraction_rules: 提取规则列表
            
        Returns:
            提取的变量字典
        """
        extracted = {}
        
        for rule in extraction_rules:
            var_name = rule.get('variable_name') or rule.get('name')
            source = rule.get('source', 'body')
            extract_type = rule.get('extract_type') or rule.get('type', 'json_path')
            expression = rule.get('expression')
            default = rule.get('default_value') or rule.get('default')
            
            if not var_name or not expression:
                continue
            
            try:
                if source == 'header':
                    value = response.headers.get(expression, default)
                elif source == 'status_code':
                    value = response.status_code
                elif source == 'body':
                    if extract_type == 'json_path':
                        try:
                            json_data = response.json()
                            value = VariableExtractor._json_path_extract(json_data, expression)
                        except:
                            value = default
                    elif extract_type == 'regex':
                        value = VariableExtractor._regex_extract(response.text, expression)
                    else:
                        value = default
                else:
                    value = default
                
                extracted[var_name] = value if value is not None else default
                
            except Exception as e:
                logger.warning(f"变量提取失败: {var_name}, 错误: {e}")
                extracted[var_name] = default
        
        return extracted
    
    @staticmethod
    def _json_path_extract(data: Any, path: str) -> Optional[Any]:
        """JSONPath提取"""
        try:
            from jsonpath_ng import parse
            matches = parse(path).find(data)
            return matches[0].value if matches else None
        except Exception:
            return None
    
    @staticmethod
    def _regex_extract(text: str, pattern: str) -> Optional[str]:
        """正则提取"""
        try:
            match = re.search(pattern, text)
            return match.group(1) if match and match.groups() else (match.group(0) if match else None)
        except Exception:
            return None


def _get_suite_data(suite_id):
    """获取测试套件数据（带缓存）"""
    suite_id = str(suite_id)
    
    if suite_id in _suite_cache:
        return _suite_cache[suite_id], _requests_cache.get(suite_id, [])
    
    test_suite = TestSuite.objects.get(id=suite_id)
    suite_requests = TestSuiteRequest.objects.filter(
        test_suite=test_suite,
        enabled=True
    ).select_related('request').order_by('order')
    
    requests_data = []
    for sr in suite_requests:
        req = sr.request
        requests_data.append({
            'id': req.id,
            'name': req.name,
            'method': req.method,
            'url': req.url,
            'headers': req.headers,
            'params': req.params,
            'body': req.body,
            'pre_request_script': req.pre_request_script,
            'post_request_script': req.post_request_script,
            'suite_request_id': sr.id,
            'suite_assertions': sr.assertions or [],
            'order': sr.order,
            'skip_condition': getattr(sr, 'skip_condition', None),
            'extract_variables': getattr(sr, 'extractors', []) or getattr(sr, 'extract_variables', []),
            'interface_extract_variables': getattr(req, 'extractors', []) or getattr(req, 'extract_variables', []),
        })
    
    _suite_cache[suite_id] = test_suite
    _requests_cache[suite_id] = requests_data
    
    return test_suite, requests_data


def _get_request_data(request_id):
    """获取单个请求数据（带缓存）"""
    request_id = str(request_id)
    
    if request_id in _requests_cache:
        return _requests_cache[request_id]
    
    api_request = ApiRequest.objects.get(id=request_id)
    request_data = {
        'id': api_request.id,
        'name': api_request.name,
        'method': api_request.method,
        'url': api_request.url,
        'headers': api_request.headers,
        'params': api_request.params,
        'body': api_request.body,
        'assertions': api_request.assertions,
        'pre_request_script': api_request.pre_request_script,
        'post_request_script': api_request.post_request_script,
    }
    
    _requests_cache[request_id] = request_data
    return request_data


def _get_environment_data(env_id):
    """获取环境数据（带缓存）"""
    if not env_id:
        return None
    
    env_id = str(env_id)
    
    if env_id in _environment_cache:
        return _environment_cache[env_id]
    
    try:
        environment = Environment.objects.get(id=env_id)
        _environment_cache[env_id] = environment
        return environment
    except Environment.DoesNotExist:
        return None


def _resolve_variables(text, variables, resolver):
    """替换文本中的变量"""
    if not isinstance(text, str):
        return text
    
    result = text
    for key, value in (variables or {}).items():
        replacement = str(value) if value is not None else ''
        result = result.replace(f'{{{{{key}}}}}', replacement)
    
    return resolver.resolve(result)


def _resolve_dict(data, variables, resolver):
    """递归解析字典中的变量"""
    if isinstance(data, dict):
        return {k: _resolve_dict(v, variables, resolver) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_dict(item, variables, resolver) for item in data]
    elif isinstance(data, str):
        return _resolve_variables(data, variables, resolver)
    else:
        return data


def _execute_assertions(response, assertions):
    """执行断言验证"""
    results = []
    
    for assertion in assertions:
        assertion_type = assertion.get('type')
        
        # 跳过无效断言（缺少 type）
        if not assertion_type:
            continue
        
        result = {
            'name': assertion.get('name', '未命名断言'),
            'type': assertion_type,
            'passed': False,
            'expected': assertion.get('expected'),
            'actual': None,
            'error': None
        }
        
        try:
            expected = assertion.get('expected')
            # 对 status_code 类型，确保 expected 为整数（前端可能存为字符串）
            if assertion_type == 'status_code' and expected is not None:
                try:
                    expected = int(expected)
                except (ValueError, TypeError):
                    result['error'] = f"expected 值无效: {expected!r}"
                    results.append(result)
                    continue
            # 对 response_time 类型，确保 expected 为数字
            if assertion_type == 'response_time' and expected is not None:
                try:
                    expected = float(expected)
                except (ValueError, TypeError):
                    result['error'] = f"expected 值无效: {expected!r}"
                    results.append(result)
                    continue
            
            if assertion_type == 'status_code':
                result['actual'] = response.status_code
                result['passed'] = result['actual'] == expected
                if not result['passed']:
                    result['error'] = f"期望状态码 {expected}, 实际 {result['actual']}"
                
            elif assertion_type == 'response_time':
                result['actual'] = assertion.get('actual_time')
                result['passed'] = result['actual'] <= expected if result['actual'] else False
                if not result['passed']:
                    result['error'] = f"期望响应时间 <= {expected}ms, 实际 {result['actual']:.2f}ms" if result['actual'] else f"无响应时间数据"
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                result['actual'] = text[:200] + '...' if len(text) > 200 else text
                result['passed'] = pattern in str(text)
                if not result['passed']:
                    result['error'] = f"响应体中不包含 '{pattern}'"
                    
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                
                try:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式")
                    
                    response_json = json.loads(response.text)
                    
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    result['actual'] = matches[0].value if matches else None
                    result['passed'] = str(result['actual']) == str(expected_value)
                    if not result['passed']:
                        result['error'] = f"JSON路径 {json_path} 期望值 {expected_value!r}, 实际 {result['actual']!r}"
                    
                except Exception as e:
                    result['error'] = str(e)
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                result['actual'] = response.headers.get(header_name)
                result['passed'] = result['actual'] == expected_value
                if not result['passed']:
                    result['error'] = f"响应头 {header_name} 期望 {expected_value!r}, 实际 {result['actual']!r}"
                    
            elif assertion_type == 'equals':
                result['actual'] = response.text.strip()
                result['passed'] = result['actual'] == str(expected).strip()
                if not result['passed']:
                    result['error'] = f"响应体不匹配: 期望 {str(expected).strip()!r}, 实际 {result['actual']!r}"
            
            elif assertion_type == 'not_empty':
                result['actual'] = len(response.text) if response.text else 0
                result['passed'] = result['actual'] > 0
                if not result['passed']:
                    result['error'] = "响应体为空"
            
            elif assertion_type == 'json_schema':
                try:
                    import jsonschema
                    schema = assertion.get('schema', {})
                    response_json = response.json()
                    jsonschema.validate(response_json, schema)
                    result['passed'] = True
                except Exception as e:
                    result['error'] = str(e)
                    result['passed'] = False
        
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def _execute_request(request_data, variables, resolver, timeout=30):
    """执行单个API请求"""
    url = _resolve_variables(request_data['url'], variables, resolver)
    
    headers = {}
    if isinstance(request_data.get('headers'), list):
        for header_item in request_data['headers']:
            if header_item.get('enabled', True) and header_item.get('key'):
                key = header_item['key']
                value = _resolve_variables(str(header_item.get('value', '')), variables, resolver)
                headers[key] = value
    elif request_data.get('headers'):
        headers = request_data['headers'].copy()
        for key, value in headers.items():
            headers[key] = _resolve_variables(str(value), variables, resolver)
    
    params = request_data.get('params', {}).copy() if request_data.get('params') else {}
    for key, value in params.items():
        params[key] = _resolve_variables(str(value), variables, resolver)
    
    body_data = None
    body_kwarg = 'json'  # requests.request 的参数名: json / data / files
    if request_data.get('body') and request_data['method'] in ['POST', 'PUT', 'PATCH']:
        body_type = request_data['body'].get('type', '')
        raw_body = request_data['body'].get('raw', '')

        if body_type == 'json':
            body_data = request_data['body'].get('data', {})
            body_data = _resolve_dict(body_data, variables, resolver)
            body_kwarg = 'json'

        elif body_type == 'x-www-form-urlencoded':
            # 表单编码: 将 data 数组转为 dict，然后做变量替换
            form_data = {}
            for item in (request_data['body'].get('data') or []):
                if not item.get('enabled', True) or not item.get('key'):
                    continue
                key = item['key']
                value = str(item.get('value', ''))
                value = _resolve_variables(value, variables, resolver)
                form_data[key] = value
            body_data = form_data
            body_kwarg = 'data'

        elif body_type == 'form-data':
            # multipart/form-data
            form_data = []
            for item in (request_data['body'].get('data') or []):
                if not item.get('enabled', True) or not item.get('key'):
                    continue
                key = item['key']
                value = _resolve_variables(str(item.get('value', '')), variables, resolver)
                form_data.append((key, (item.get('filename', ''), value, item.get('content_type', '')) if item.get('type') == 'file' else (key, value)))
            body_data = form_data
            body_kwarg = 'files' if any(item.get('type') == 'file' for item in (request_data['body'].get('data') or [])) else 'data'

        elif body_type == 'raw':
            # 原始文本/XML 等
            body_data = raw_body
            if isinstance(body_data, str):
                body_data = _resolve_variables(body_data, variables, resolver)
            body_kwarg = 'data'

        elif body_type == 'none' or not body_type:
            body_data = None

    start_time = time.time()
    req_kwargs = {
        'method': request_data['method'],
        'url': url,
        'headers': headers,
        'params': params,
        'timeout': timeout,
    }
    if body_data is not None:
        req_kwargs[body_kwarg] = body_data

    response = requests.request(**req_kwargs)
    end_time = time.time()
    response_time = (end_time - start_time) * 1000
    
    # 套件执行时只使用套件配置中的断言（不合并接口断言）
    # 接口断言通过"同步接口数据"已复制到 TestSuiteRequest.assertions
    all_assertions = request_data.get('suite_assertions') or []

    for assertion in all_assertions:
        if assertion.get('type') == 'response_time':
            assertion['actual_time'] = response_time

    assertions_results = _execute_assertions(response, all_assertions)
    
    passed = all(ar.get('passed', True) for ar in assertions_results) if assertions_results else True
    error_message = ''
    
    if not passed:
        for ar in assertions_results:
            if not ar.get('passed'):
                error_detail = f"期望: {ar.get('expected')}, 实际: {ar.get('actual')}" if ar.get('error') is None else ar.get('error')
                error_message = f"{ar['name']}: {error_detail}"
                break
    
    return {
        'status_code': response.status_code,
        'response_time': response_time,
        'passed': passed,
        'error': error_message,
        'assertions_results': assertions_results,
        'response_body': response.text[:1000] if response.text else '',
        'response': response,
    }


def pytest_generate_tests(metafunc):
    """动态生成测试用例参数"""
    if 'request_index' in metafunc.fixturenames:
        suite_id = os.environ.get('API_TEST_SUITE_ID')
        if suite_id:
            try:
                _, requests_data = _get_suite_data(suite_id)
                request_ids = [f"req_{i}_{req['id']}_{req['name'][:20]}" for i, req in enumerate(requests_data)]
                metafunc.parametrize('request_index', list(range(len(requests_data))), ids=request_ids)
            except Exception as e:
                logger.error(f"获取测试请求失败: {e}")
                metafunc.parametrize('request_index', [])


@pytest.fixture(scope="session")
def suite_data(api_test_suite_id):
    """获取测试套件数据"""
    if not api_test_suite_id:
        return None
    test_suite, _ = _get_suite_data(api_test_suite_id)
    return test_suite


@pytest.fixture(scope="session")
def all_requests(api_test_suite_id):
    """获取所有请求数据"""
    if not api_test_suite_id:
        return []
    _, requests_data = _get_suite_data(api_test_suite_id)
    return requests_data


@pytest.fixture(scope="function")
def request_data(request_index, all_requests):
    """获取当前请求数据"""
    if request_index < len(all_requests):
        return all_requests[request_index]
    return None


@pytest.fixture(scope="session")
def session_variables():
    """会话级变量（跨请求传递）"""
    return _session_variables


@pytest.fixture(scope="session")
def variables(api_test_suite_id, api_environment_id, session_variables):
    """获取环境变量"""
    resolver = VariableResolver()
    vars_dict = dict(session_variables)
    
    global_env = Environment.objects.filter(scope='GLOBAL', is_active=True).first()
    if global_env and global_env.variables:
        for key, val in global_env.variables.items():
            if isinstance(val, dict) and 'currentValue' in val:
                vars_dict[key] = val['currentValue']
            else:
                vars_dict[key] = val
    
    if api_test_suite_id:
        test_suite, _ = _get_suite_data(api_test_suite_id)
        if test_suite and test_suite.environment:
            env = test_suite.environment
            if env.variables:
                for key, val in env.variables.items():
                    if isinstance(val, dict) and 'currentValue' in val:
                        vars_dict[key] = val['currentValue']
                    else:
                        vars_dict[key] = val
    
    if api_environment_id:
        env = _get_environment_data(api_environment_id)
        if env and env.variables:
            for key, val in env.variables.items():
                if isinstance(val, dict) and 'currentValue' in val:
                    vars_dict[key] = val['currentValue']
                else:
                    vars_dict[key] = val
    
    return vars_dict


@pytest.fixture(scope="session")
def resolver():
    """变量解析器"""
    return VariableResolver()


@allure.feature("API自动化测试")
def test_api_request(request_index, request_data, suite_data, variables, resolver, api_timeout, api_username, session_variables):
    """API 自动化测试主入口"""
    if not request_data:
        pytest.skip("无测试请求数据")
    
    request_name = request_data['name']
    request_method = request_data['method']
    
    allure.dynamic.title(f"[{request_method}] {request_name}")
    allure.dynamic.suite(suite_data.name if suite_data else "API自动化测试")
    
    allure.dynamic.label('method', request_method)
    allure.dynamic.label('executor', api_username)
    
    skip_condition = request_data.get('skip_condition')
    if skip_condition:
        try:
            should_skip = eval(skip_condition, {"variables": variables})
            if should_skip:
                pytest.skip(f"满足跳过条件: {skip_condition}")
        except Exception as e:
            allure.attach(f"跳过条件评估失败: {e}", name="警告", attachment_type=allure.attachment_type.TEXT)
    
    pre_script = request_data.get('pre_request_script')
    if pre_script:
        with allure.step("执行前置脚本"):
            script_result = ScriptExecutor.execute_pre_request(pre_script, {
                'variables': variables,
                'request': request_data,
            })
            
            if script_result['logs']:
                allure.attach('\n'.join(script_result['logs']), name="脚本日志", attachment_type=allure.attachment_type.TEXT)
            
            if script_result['variables']:
                variables.update(script_result['variables'])
                session_variables.update(script_result['variables'])
                allure.attach(json.dumps(script_result['variables'], ensure_ascii=False), name="设置的变量", attachment_type=allure.attachment_type.JSON)
            
            if not script_result['success']:
                allure.attach(script_result['error'], name="脚本错误", attachment_type=allure.attachment_type.TEXT)
    
    with allure.step(f"准备请求: {request_name}"):
        allure.attach(
            f"方法: {request_method}\nURL: {request_data['url']}",
            name="请求信息",
            attachment_type=allure.attachment_type.TEXT
        )
    
    result = _execute_request(request_data, variables, resolver, api_timeout)
    response = result.pop('response')
    
    # 将 method、url、status_code、response_time 写入 Allure parameters，供 _parse_allure_results 提取
    allure.dynamic.parameter('url', request_data['url'])
    allure.dynamic.parameter('status_code', str(result['status_code']))
    allure.dynamic.parameter('response_time', f"{result['response_time']:.2f}")
    
    with allure.step(f"发送请求: {request_method} {request_data['url']}"):
        allure.attach(
            f"状态码: {result['status_code']}\n响应时间: {result['response_time']:.2f}ms",
            name="响应信息",
            attachment_type=allure.attachment_type.TEXT
        )
    
    if result['response_body']:
        try:
            json_body = json.loads(result['response_body'])
            allure.attach(
                json.dumps(json_body, ensure_ascii=False, indent=2),
                name="响应体",
                attachment_type=allure.attachment_type.JSON
            )
        except:
            allure.attach(
                result['response_body'],
                name="响应体",
                attachment_type=allure.attachment_type.TEXT
            )
    
    for assertion_result in result.get('assertions_results', []):
        status = 'passed' if assertion_result['passed'] else 'failed'
        with allure.step(f"断言: {assertion_result['name']}"):
            allure.attach(
                f"类型: {assertion_result['type']}\n"
                f"期望: {assertion_result['expected']}\n"
                f"实际: {assertion_result['actual']}\n"
                f"状态: {status}",
                name="断言详情",
                attachment_type=allure.attachment_type.TEXT
            )
            if assertion_result.get('error'):
                allure.attach(
                    assertion_result['error'],
                    name="错误信息",
                    attachment_type=allure.attachment_type.TEXT
                )
    
    post_script = request_data.get('post_request_script')
    if post_script:
        with allure.step("执行后置脚本"):
            try:
                response_json = response.json()
            except:
                response_json = None
            
            script_result = ScriptExecutor.execute_post_request(post_script, {
                'variables': variables,
                'response': {
                    'status_code': result['status_code'],
                    'headers': dict(response.headers),
                    'body': result['response_body'],
                },
                'response_json': response_json,
                'status_code': result['status_code'],
                'response_time': result['response_time'],
                'request': request_data,
            })
            
            if script_result['logs']:
                allure.attach('\n'.join(script_result['logs']), name="脚本日志", attachment_type=allure.attachment_type.TEXT)
            
            if script_result['variables']:
                variables.update(script_result['variables'])
                session_variables.update(script_result['variables'])
                allure.attach(json.dumps(script_result['variables'], ensure_ascii=False), name="提取的变量", attachment_type=allure.attachment_type.JSON)
            
            if not script_result['success']:
                allure.attach(script_result['error'], name="脚本错误", attachment_type=allure.attachment_type.TEXT)
    
    # 合并接口层 + 套件层的变量提取
    extract_rules = request_data.get('extract_variables') or []
    interface_extract_rules = request_data.get('interface_extract_variables') or []
    all_extract_rules = interface_extract_rules + extract_rules
    if all_extract_rules:
        with allure.step("提取变量"):
            extracted = VariableExtractor.extract_from_response(response, all_extract_rules)
            if extracted:
                variables.update(extracted)
                session_variables.update(extracted)
                allure.attach(json.dumps(extracted, ensure_ascii=False), name="提取的变量", attachment_type=allure.attachment_type.JSON)
    
    if not result['passed']:
        allure.attach(
            result['error'],
            name="请求失败",
            attachment_type=allure.attachment_type.TEXT
        )
    
    assert result['passed'], f"请求执行失败: {result['error']}"
    
    allure.attach(
        f"请求: {request_name}\n状态码: {result['status_code']}\n响应时间: {result['response_time']:.2f}ms",
        name="执行统计",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.feature("API自动化测试")
def test_api_single_request(api_request_id, variables, resolver, api_timeout, api_username, session_variables):
    """单个API请求测试入口"""
    if not api_request_id:
        pytest.skip("无API请求ID")
    
    request_data = _get_request_data(api_request_id)
    
    request_name = request_data['name']
    request_method = request_data['method']
    
    allure.dynamic.title(f"[{request_method}] {request_name}")
    allure.dynamic.suite("单个API请求测试")
    
    allure.dynamic.label('method', request_method)
    allure.dynamic.label('executor', api_username)
    
    pre_script = request_data.get('pre_request_script')
    if pre_script:
        with allure.step("执行前置脚本"):
            script_result = ScriptExecutor.execute_pre_request(pre_script, {
                'variables': variables,
                'request': request_data,
            })
            
            if script_result['variables']:
                variables.update(script_result['variables'])
                session_variables.update(script_result['variables'])
            
            if not script_result['success']:
                allure.attach(script_result['error'], name="脚本错误", attachment_type=allure.attachment_type.TEXT)
    
    with allure.step(f"准备请求: {request_name}"):
        allure.attach(
            f"方法: {request_method}\nURL: {request_data['url']}",
            name="请求信息",
            attachment_type=allure.attachment_type.TEXT
        )
    
    result = _execute_request(request_data, variables, resolver, api_timeout)
    response = result.pop('response')
    
    with allure.step(f"发送请求: {request_method} {request_data['url']}"):
        allure.attach(
            f"状态码: {result['status_code']}\n响应时间: {result['response_time']:.2f}ms",
            name="响应信息",
            attachment_type=allure.attachment_type.TEXT
        )
    
    if result['response_body']:
        try:
            json_body = json.loads(result['response_body'])
            allure.attach(
                json.dumps(json_body, ensure_ascii=False, indent=2),
                name="响应体",
                attachment_type=allure.attachment_type.JSON
            )
        except:
            allure.attach(
                result['response_body'],
                name="响应体",
                attachment_type=allure.attachment_type.TEXT
            )
    
    for assertion_result in result.get('assertions_results', []):
        status = 'passed' if assertion_result['passed'] else 'failed'
        with allure.step(f"断言: {assertion_result['name']}"):
            allure.attach(
                f"类型: {assertion_result['type']}\n"
                f"期望: {assertion_result['expected']}\n"
                f"实际: {assertion_result['actual']}\n"
                f"状态: {status}",
                name="断言详情",
                attachment_type=allure.attachment_type.TEXT
            )
    
    post_script = request_data.get('post_request_script')
    if post_script:
        with allure.step("执行后置脚本"):
            try:
                response_json = response.json()
            except:
                response_json = None
            
            script_result = ScriptExecutor.execute_post_request(post_script, {
                'variables': variables,
                'response': {
                    'status_code': result['status_code'],
                    'headers': dict(response.headers),
                    'body': result['response_body'],
                },
                'response_json': response_json,
                'status_code': result['status_code'],
                'response_time': result['response_time'],
                'request': request_data,
            })
            
            if script_result['variables']:
                variables.update(script_result['variables'])
                session_variables.update(script_result['variables'])
    
    assert result['passed'], f"请求执行失败: {result['error']}"
