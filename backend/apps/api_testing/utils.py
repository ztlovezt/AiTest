import json
import time
from django.utils import timezone
from .models import RequestHistory
from .variable_resolver import VariableResolver


def _safe_json_parse(response):
    """安全解析 response.json()，避免 JSONDecodeError"""
    if not response.headers.get('content-type', '').startswith('application/json'):
        return None
    try:
        return response.json()
    except (ValueError, Exception):
        return None


def execute_assertions(response, assertions):
    """执行断言验证 - 支持8种断言类型"""
    results = []
    
    for assertion in assertions:
        assertion_type = assertion.get('type')
        # 跳过无效断言
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
            actual = None
            passed = False
            
            if assertion_type == 'status_code':
                actual = response.status_code
                # 类型安全：强制int转换
                expected = int(expected) if expected is not None else expected
                passed = actual == expected
                
            elif assertion_type == 'response_time':
                actual = assertion.get('actual_time')
                # 类型安全：强制float转换
                expected = float(expected) if expected is not None else 0
                passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                actual = None
                passed = False
                
                try:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")
                    
                    response_json = json.loads(response.text)
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual) == str(expected_value)
                    result['actual'] = actual
                except json.JSONDecodeError as e:
                    result['error'] = f"JSON解析失败: {str(e)}"
                except ImportError as e:
                    result['error'] = f"缺少依赖库: {str(e)}，请安装jsonpath-ng"
                except Exception as e:
                    result['error'] = f"执行错误: {str(e)}"
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                actual = response.headers.get(header_name)
                passed = actual == expected_value
                
            elif assertion_type == 'equals':
                actual = response.text.strip()
                passed = actual == str(expected).strip()
            
            elif assertion_type == 'not_empty':
                actual = len(response.text) if response.text else 0
                passed = actual > 0
                if not passed:
                    result['error'] = '响应体为空'
            
            elif assertion_type == 'json_schema':
                try:
                    import jsonschema
                    schema = assertion.get('schema', {})
                    response_json = response.json()
                    jsonschema.validate(response_json, schema)
                    actual = 'valid'
                    passed = True
                except ImportError:
                    result['error'] = '缺少 jsonschema 库，请执行 pip install jsonschema'
                except jsonschema.ValidationError as e:
                    result['error'] = f'JSON Schema 验证失败: {e.message}'
                    passed = False
                except Exception as e:
                    result['error'] = f'JSON Schema 验证错误: {str(e)}'
                    passed = False
            
            if 'actual' not in result or result['actual'] is None:
                result['actual'] = actual
            result['passed'] = passed
            
            # 设置有意义的错误消息
            if not passed and not result['error']:
                if assertion_type == 'status_code':
                    result['error'] = f'期望状态码 {expected}, 实际 {actual}'
                elif assertion_type == 'response_time':
                    result['error'] = f'响应时间 {actual}ms 超过期望值 {expected}ms'
                elif assertion_type == 'contains':
                    result['error'] = f'响应体中未找到: {expected}'
                elif assertion_type == 'equals':
                    result['error'] = f'期望值 "{expected}" 不等于实际值 "{actual}"'
                else:
                    result['error'] = f'{assertion_type} 断言不通过'
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def _generate_allure_report_sync(execution_id: int):
    """同步生成 Allure 报告（用于定时任务等场景）"""
    from .models import TestExecution
    
    try:
        execution = TestExecution.objects.get(id=execution_id)
        generate_allure_report_for_execution(execution)
        logger.info(f"[execute_test_suite] Allure 报告生成成功: execution_{execution_id}")
    except TestExecution.DoesNotExist:
        logger.error(f"[execute_test_suite] 执行记录不存在: execution_{execution_id}")
    except Exception as e:
        logger.error(f"[execute_test_suite] 生成 Allure 报告失败: {e}", exc_info=True)


def execute_test_suite(test_suite, environment, executed_by, async_report=True):
    """执行测试套件并返回结果"""
    from .models import TestExecution, RequestHistory
    import requests
    import time
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 创建执行记录
        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by
        )
        
        # 获取套件中的请求
        suite_requests = test_suite.testsuiterequest_set.filter(enabled=True).order_by('order')
        
        execution.total_requests = suite_requests.count()
        execution.save()
        
        results = []
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        
        # 会话变量：存储提取的变量，供后续请求使用
        session_variables = {}
        
        # 执行每个请求
        for suite_request in suite_requests:
            api_request = suite_request.request
            
            try:
                # 解析环境变量
                variables = {}
                if environment:
                    variables.update(environment.variables)
                
                # 合并会话变量（会话变量优先级高于环境变量）
                variables.update(session_variables)
                
                # 替换URL中的变量（先解析动态函数，再替换环境变量）
                url = _replace_variables(api_request.url, variables)
                url = resolver.resolve(url)
                
                # 准备请求头
                headers = {}
                if isinstance(api_request.headers, list):
                    for header_item in api_request.headers:
                        if header_item.get('enabled', True) and header_item.get('key'):
                            key = header_item['key']
                            value = _replace_variables(str(header_item.get('value', '')), variables)
                            value = resolver.resolve(value)
                            headers[key] = value
                elif api_request.headers:
                    headers = api_request.headers.copy()
                    for key, value in headers.items():
                        headers[key] = _replace_variables(str(value), variables)
                        headers[key] = resolver.resolve(headers[key])
                
                # 准备请求参数
                params = api_request.params.copy() if api_request.params else {}
                for key, value in params.items():
                    params[key] = _replace_variables(str(value), variables)
                    params[key] = resolver.resolve(params[key])
                
                # 准备请求体
                body_data = None
                if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
                    if api_request.body.get('type') == 'json':
                        body_data = api_request.body.get('data', {})
                        body_data = _replace_variables_in_dict(body_data, variables)
                        body_data = _resolve_variables_in_dict(body_data, resolver)
                
                # 执行请求
                start_time = time.time()
                response = requests.request(
                    method=api_request.method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body_data,
                    timeout=30
                )
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 执行套件级断言验证（只读suite_request.assertions，不合并接口断言）
                suite_assertions = suite_request.assertions or []
                assertions_results = execute_assertions(response, suite_assertions)
                # 同时执行接口断言并将结果合并
                api_assertions = api_request.assertions or []
                api_assertion_results = execute_assertions(response, api_assertions)
                
                # 检查所有断言是否通过
                passed = True
                error_message = ''
                
                # 检查套件请求的断言
                for assertion in suite_request.assertions:
                    if assertion.get('type') == 'status_code':
                        expected = assertion.get('expected')
                        if expected is not None:
                            expected = int(expected)
                        if response.status_code != expected:
                            passed = False
                            error_message = f'状态码断言失败: 期望 {expected}, 实际 {response.status_code}'
                            break
                
                # 检查接口自身的断言
                if passed and api_assertion_results:
                    for assertion_result in api_assertion_results:
                        if not assertion_result.get('passed', True):
                            passed = False
                            error_message = f"断言失败: {assertion_result.get('name', '未命名断言')} - {assertion_result.get('error', '断言不通过')}"
                            break
                
                # 执行变量提取 - 优先使用 extractors 字段
                extractors_config = suite_request.extractors or suite_request.extract_variables or []
                if not extractors_config:
                    # 如果套件请求没有提取器，尝试使用接口的提取器
                    extractors_config = api_request.extractors or api_request.extract_variables or []
                
                if extractors_config:
                    from .extractor import extract_variables as do_extract
                    extracted_vars, _ = do_extract(response, extractors_config)
                    if extracted_vars:
                        session_variables.update(extracted_vars)
                        logger.info(f"[execute_test_suite] 提取变量: {list(extracted_vars.keys())}")
                
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'passed': passed,
                    'error': error_message,
                    'assertions_results': assertions_results
                })
                
                # 保存请求历史
                RequestHistory.objects.create(
                    request=api_request,
                    environment=environment,
                    request_data={
                        'url': url,
                        'method': api_request.method,
                        'headers': headers,
                        'params': params,
                        'body': body_data
                    },
                    response_data={
                        'headers': dict(response.headers),
                        'body': response.text,
                        'json': _safe_json_parse(response)
                    },
                    status_code=response.status_code,
                    response_time=response_time,
                    assertions_results=assertions_results,
                    executed_by=executed_by
                )
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': api_request.url,
                    'passed': False,
                    'error': str(e)
                })
        
        # 更新执行结果 - 三段式状态判断
        execution.end_time = timezone.now()
        execution.passed_requests = passed_count
        execution.failed_requests = failed_count
        execution.skipped_requests = skipped_count
        execution.results = results
        
        if failed_count == 0 and passed_count > 0:
            execution.status = 'COMPLETED'
        elif passed_count == 0 and failed_count > 0:
            execution.status = 'FAILED'
        elif failed_count > 0 and passed_count > 0:
            execution.status = 'PARTIAL_FAILED'
        else:
            execution.status = 'COMPLETED'  # 无请求的情况
        execution.save()
        
        # 生成 Allure 报告（同步或异步）
        if async_report:
            # 后台线程生成报告
            import threading
            thread = threading.Thread(
                target=_generate_allure_report_sync,
                args=(execution.id,),
                daemon=True
            )
            thread.start()
            logger.info(f"[execute_test_suite] 报告生成已提交到后台线程: execution_{execution.id}")
        else:
            # 同步生成报告
            _generate_allure_report_sync(execution.id)
        
        # 计算执行时长
        duration = 0
        if execution.start_time and execution.end_time:
            duration = (execution.end_time - execution.start_time).total_seconds()
        
        # 格式化开始时间和结束时间
        from django.utils import timezone as tz
        start_time_str = tz.localtime(execution.start_time).strftime('%Y-%m-%d %H:%M:%S') if execution.start_time else None
        end_time_str = tz.localtime(execution.end_time).strftime('%Y-%m-%d %H:%M:%S') if execution.end_time else None
        
        return {
            'success': True,
            'execution_id': execution.id,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'skipped_count': skipped_count,
            'total_count': execution.total_requests,
            'total_requests': execution.total_requests,
            'project_name': test_suite.project.name if test_suite.project else '',
            'duration': duration,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"执行测试套件失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def execute_api_request(api_request, environment, executed_by):
    """执行单个API请求并返回结果"""
    import requests
    import time
    import base64
    from io import BytesIO
    
    try:
        resolver = VariableResolver()
        
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        url = _replace_variables(api_request.url, variables)
        url = resolver.resolve(url)
        
        headers = {}
        if isinstance(api_request.headers, list):
            for header_item in api_request.headers:
                if header_item.get('enabled', True) and header_item.get('key'):
                    key = header_item['key']
                    value = _replace_variables(str(header_item.get('value', '')), variables)
                    value = resolver.resolve(value)
                    headers[key] = value
        elif api_request.headers:
            headers = api_request.headers.copy()
            for key, value in headers.items():
                headers[key] = _replace_variables(str(value), variables)
                headers[key] = resolver.resolve(headers[key])
        
        params = api_request.params.copy() if api_request.params else {}
        for key, value in params.items():
            params[key] = _replace_variables(str(value), variables)
            params[key] = resolver.resolve(params[key])
        
        body_data = None
        body_kwarg = 'json'
        files_data = None
        body_type = ''
        
        if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
            body_type = api_request.body.get('type', '')
            
            if body_type == 'json':
                body_data = api_request.body.get('data', {})
                body_data = _replace_variables_in_dict(body_data, variables)
                body_data = _resolve_variables_in_dict(body_data, resolver)
                body_kwarg = 'json'
            
            elif body_type == 'x-www-form-urlencoded':
                form_data = {}
                for item in (api_request.body.get('data') or []):
                    if item.get('enabled', True) and item.get('key'):
                        key = item['key']
                        value = _replace_variables(str(item.get('value', '')), variables)
                        value = resolver.resolve(value)
                        form_data[key] = value
                body_data = form_data
                body_kwarg = 'data'
            
            elif body_type == 'form-data':
                form_data = {}
                files_data = {}
                
                for item in (api_request.body.get('data') or []):
                    if not item.get('enabled', True) or not item.get('key'):
                        continue
                    key = item['key']
                    
                    if item.get('type') == 'file' and item.get('fileData'):
                        filename = item.get('filename', item.get('value', 'file'))
                        content_type = item.get('contentType', 'application/octet-stream')
                        try:
                            file_bytes = base64.b64decode(item['fileData'])
                            files_data[key] = (filename, BytesIO(file_bytes), content_type)
                            logger.info(f"[API测试] 文件上传: key={key}, filename={filename}, size={len(file_bytes)} bytes")
                        except Exception as e:
                            logger.error(f"[API测试] 文件解码失败: key={key}, error={e}")
                            form_data[key] = item.get('value', '')
                    else:
                        value = _replace_variables(str(item.get('value', '')), variables)
                        value = resolver.resolve(value)
                        form_data[key] = value
                
                body_data = form_data if form_data else None
                body_kwarg = 'data'
                if files_data:
                    body_data = form_data if form_data else {}
                    body_kwarg = 'files'
                    body_data.update(files_data)
            
            elif body_type == 'raw':
                raw_body = api_request.body.get('raw', '')
                body_data = _replace_variables(raw_body, variables) if isinstance(raw_body, str) else raw_body
                body_data = resolver.resolve(body_data) if isinstance(body_data, str) else body_data
                body_kwarg = 'data'
        
        def serialize_body_data(data, body_type_str):
            if not isinstance(data, dict):
                return data
            result = {}
            for key, value in data.items():
                if isinstance(value, tuple) and len(value) == 3:
                    filename, file_obj, content_type = value
                    if hasattr(file_obj, 'getbuffer'):
                        file_size = len(file_obj.getbuffer())
                    else:
                        file_size = 0
                    result[key] = f"[文件] {filename} ({file_size} bytes)"
                elif hasattr(value, 'read'):
                    result[key] = f"[文件对象] {key}"
                else:
                    result[key] = value
            return result
        
        request_kwargs = {
            'method': api_request.method,
            'url': url,
            'headers': headers,
            'params': params,
            'timeout': 30
        }
        
        if body_data is not None:
            request_kwargs[body_kwarg] = body_data
        
        start_time = time.time()
        start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        response = requests.request(**request_kwargs)
        end_time = time.time()
        end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
        response_time = (end_time - start_time) * 1000
        
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        assertions_results = execute_assertions(response, assertions)
        
        serializable_body_data = serialize_body_data(body_data, body_type) if body_type == 'form-data' and body_data else body_data
        
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': api_request.method,
                'headers': headers,
                'params': params,
                'body': serializable_body_data
            },
            response_data={
                'headers': dict(response.headers),
                'body': response.text,
                'json': _safe_json_parse(response)
            },
            status_code=response.status_code,
            response_time=response_time,
            assertions_results=assertions_results,
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': response.status_code,
            'response_time': response_time,
            'duration': response_time / 1000 if response_time else 0,
            'start_time': start_time_str,
            'end_time': end_time_str,
            'assertions_results': assertions_results,
            'response_data': {
                'headers': dict(response.headers),
                'body': response.text,
                'json': _safe_json_parse(response)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _replace_variables(text, variables):
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

def _replace_variables_in_dict(data, variables):
    """递归替换字典中的变量"""
    if isinstance(data, dict):
        return {k: _replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_variables_in_dict(item, variables) for item in data]
    elif isinstance(data, str):
        return _replace_variables(data, variables)
    else:
        return data

def _resolve_variables_in_dict(data, resolver):
    """递归解析字典中的动态函数占位符"""
    if isinstance(data, dict):
        return {k: _resolve_variables_in_dict(v, resolver) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_variables_in_dict(item, resolver) for item in data]
    elif isinstance(data, str):
        return resolver.resolve(data)
    else:
        return data


# ================ Allure 报告生成函数 ================

import os
import subprocess
import shutil
import logging

logger = logging.getLogger(__name__)


def _check_java_environment():
    """检查 Java 环境是否可用"""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _generate_allure_result_files(execution, results_dir):
    """从 execution.results 生成 Allure 结果 JSON 文件"""
    import json as json_module
    import uuid as uuid_module
    
    os.makedirs(results_dir, exist_ok=True)
    
    results = execution.results or []
    
    for result in results:
        test_uuid = str(uuid_module.uuid4())
        
        start_ms = int(execution.start_time.timestamp() * 1000) if execution.start_time else None
        stop_ms = int(execution.end_time.timestamp() * 1000) if execution.end_time else None
        
        allure_result = {
            'uuid': test_uuid,
            'name': result.get('name', 'API请求'),
            'fullName': f'API Test Suite - {result.get("method", "")} {result.get("url", "")}',
            'historyId': f'{test_uuid}',
            'status': 'passed' if result.get('passed') else 'failed',
            'stage': 'finished',
            'start': start_ms,
            'stop': stop_ms,
            'labels': [
                {'name': 'suite', 'value': execution.test_suite.name if execution.test_suite else 'API Test Suite'},
                {'name': 'method', 'value': result.get('method', '')},
                {'name': 'epic', 'value': 'API Testing'},
                {'name': 'framework', 'value': 'TestHub'},
            ],
            'parameters': [
                {'name': 'url', 'value': result.get('url', '')},
                {'name': 'status_code', 'value': str(result.get('status_code', ''))},
                {'name': 'response_time', 'value': f"{result.get('response_time', 0):.2f}ms"},
            ],
            'steps': [],
        }
        
        assertions_results = result.get('assertions_results', [])
        for ar in assertions_results:
            step = {
                'name': ar.get('name', '断言'),
                'status': 'passed' if ar.get('passed') else 'failed',
                'start': start_ms,
                'stop': stop_ms,
                'stage': 'finished',
            }
            if not ar.get('passed'):
                step['statusDetails'] = {'message': ar.get('error', '断言失败')}
            allure_result['steps'].append(step)
        
        if not result.get('passed'):
            allure_result['statusDetails'] = {
                'known': False,
                'muted': False,
                'flaky': False,
                'message': result.get('error', '测试失败')
            }
        
        result_file = os.path.join(results_dir, f'{test_uuid}-result.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json_module.dump(allure_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"生成 Allure 结果文件: {result_file}")


def generate_allure_report_for_execution(execution):
    """为执行记录生成 Allure 报告（常规+single-file）"""
    from .models import ApiProject
    
    try:
        # 1. 设置状态为生成中
        execution.report_status = 'GENERATING'
        execution.save(update_fields=['report_status'])
        
        # 2. 检查 Java 环境
        if not _check_java_environment():
            logger.warning(f"Java 环境不可用，跳过报告生成: execution_{execution.id}")
            execution.report_status = 'SKIPPED'
            execution.save(update_fields=['report_status'])
            return
        
        # 3. 构建路径（与 executor.py 保持一致）
        from django.conf import settings
        results_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_RESULTS_DIR, f'execution_{execution.id}')
        report_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_REPORTS_DIR, f'execution_{execution.id}')
        single_file_dir = os.path.join(settings.MEDIA_ROOT, settings.ALLURE_API_TESTING, settings.ALLURE_SINGLE_FILE_DIR, f'execution_{execution.id}')
        
        # 清空旧结果
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)
        
        # 4. 生成结果文件和 environment.xml
        _generate_allure_result_files(execution, results_dir)
        
        # 写入 environment.xml
        env_xml = '''<?xml version='1.0' encoding='utf-8'?>
<environment xmlns="urn:model.commons.qatools.yandex.ru">
  <parameter>
    <name>Platform</name>
    <key>Platform</key>
    <value>TestHub</value>
  </parameter>
  <parameter>
    <name>Module</name>
    <key>Module</key>
    <value>API Testing</value>
  </parameter>
</environment>'''
        with open(os.path.join(results_dir, 'environment.xml'), 'w', encoding='utf-8') as f:
            f.write(env_xml)
        
        # 写入 executor.json
        executor_info = {
            "name": "TestHub",
            "type": "TestHub",
            "buildName": f"API Test Suite - execution_{execution.id}",
            "reportUrl": f"/api/api-testing-reports/execution_{execution.id}/index.html"
        }
        with open(os.path.join(results_dir, 'executor.json'), 'w', encoding='utf-8') as f:
            json.dump(executor_info, f, ensure_ascii=False, indent=2)
        
        # 5. 生成 Allure HTML 报告
        if os.path.exists(report_dir):
            shutil.rmtree(report_dir)
        os.makedirs(report_dir, exist_ok=True)
        
        if os.name == 'nt':
            cmd = f'allure generate "{results_dir}" -o "{report_dir}" --clean'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        else:
            cmd = ['allure', 'generate', results_dir, '-o', report_dir, '--clean']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        
        if result.returncode != 0:
            logger.warning(f"Allure 报告生成失败: {result.stderr}")
        
        # 6. 生成 single-file 报告
        os.makedirs(single_file_dir, exist_ok=True)
        
        if os.name == 'nt':
            single_cmd = f'allure generate "{results_dir}" -o "{single_file_dir}" --clean --single-file'
            single_result = subprocess.run(single_cmd, shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        else:
            single_cmd = ['allure', 'generate', results_dir, '-o', single_file_dir, '--clean', '--single-file']
            single_result = subprocess.run(single_cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        if single_result.returncode == 0:
            logger.info(f"Allure single-file 报告生成成功: {single_file_dir}")
        else:
            logger.warning(f"Allure single-file 报告生成失败: {single_result.stderr}")
        
        # 7. 更新状态
        execution.report_status = 'SUCCESS'
        execution.report_url = f'/api/api-testing-reports/execution_{execution.id}/index.html'
        execution.save(update_fields=['report_status', 'report_url'])
        
        logger.info(f"Allure 报告生成成功: execution_{execution.id}")
        logger.info(f"  结果目录: {results_dir}")
        logger.info(f"  报告目录: {report_dir}")
        logger.info(f"  单文件目录: {single_file_dir}")
        
    except Exception as e:
        logger.error(f"Allure 报告生成失败 execution_{execution.id}: {str(e)}", exc_info=True)
        try:
            execution.report_status = 'FAILED'
            execution.save(update_fields=['report_status'])
        except:
            pass
