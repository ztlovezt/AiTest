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
        
        # 执行每个请求
        for suite_request in suite_requests:
            api_request = suite_request.request
            
            try:
                # 解析环境变量
                variables = {}
                if environment:
                    variables.update(environment.variables)
                
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
                        expected = assertion.get('value')
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
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 解析环境变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
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
        start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
        response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=30
        )
        end_time = time.time()
        end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
        response_time = (end_time - start_time) * 1000
        
        # 执行断言验证
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        assertions_results = execute_assertions(response, assertions)
        
        # 保存请求历史
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
    
    os.makedirs(results_dir, exist_ok=True)
    
    results = execution.results or []
    test_index = 1
    
    for result in results:
        allure_result = {
            'uuid': f'{execution.id}-{test_index}',
            'name': result.get('name', f'请求{test_index}'),
            'fullName': f'API Test Suite - {result.get("method", "")} {result.get("url", "")}',
            'status': 'passed' if result.get('passed') else 'failed',
            'stage': 'finished',
            'start': execution.start_time.isoformat() + 'Z' if execution.start_time else None,
            'stop': execution.end_time.isoformat() + 'Z' if execution.end_time else None,
            'labels': [
                {'name': 'suite', 'value': execution.test_suite.name},
                {'name': 'method', 'value': result.get('method', '')},
                {'name': 'epic', 'value': 'API Testing'},
            ],
            'parameters': [
                {'name': 'url', 'value': result.get('url', '')},
                {'name': 'status_code', 'value': str(result.get('status_code', ''))},
                {'name': 'response_time', 'value': f"{result.get('response_time', 0):.2f}"},
            ],
            'steps': [],
        }
        
        # 添加断言步骤
        assertions_results = result.get('assertions_results', [])
        for ar in assertions_results:
            step = {
                'name': ar.get('name', '断言'),
                'status': 'passed' if ar.get('passed') else 'failed',
                'start': execution.start_time.isoformat() + 'Z' if execution.start_time else None,
                'stop': execution.end_time.isoformat() + 'Z' if execution.end_time else None,
                'stage': 'finished',
            }
            if not ar.get('passed'):
                step['statusDetails'] = {'message': ar.get('error', '断言失败')}
            allure_result['steps'].append(step)
        
        # 如果测试失败，添加错误信息
        if not result.get('passed'):
            allure_result['statusDetails'] = {'message': result.get('error', '测试失败')}
        
        # 写入 JSON 文件
        result_file = os.path.join(results_dir, f'result-{test_index}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json_module.dump(allure_result, f, ensure_ascii=False, indent=2)
        
        test_index += 1


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
        
        # 3. 构建路径
        module_name = 'api_testing'
        from django.conf import settings
        base_dir = settings.MEDIA_ROOT
        report_dir = os.path.join(base_dir, module_name, 'allure-reports', f'execution_{execution.id}')
        results_dir = os.path.join(report_dir, 'allure-results')
        
        # 清空旧结果
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)
        
        # 4. 生成结果文件和 environment.xml
        _generate_allure_result_files(execution, results_dir)
        
        # 写入 environment.xml
        env_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<environment xmlns="urn:model.commons.qatools.yandex.ru">
  <parameter>
    <name>Platform</name>
    <key>platform</key>
    <value>TestHub</value>
  </parameter>
  <parameter>
    <name>Module</name>
    <key>module</key>
    <value>API Testing</value>
  </parameter>
</environment>'''
        with open(os.path.join(results_dir, 'environment.xml'), 'w', encoding='utf-8') as f:
            f.write(env_xml)
        
        # 5. 生成 Allure HTML 报告
        output_dir = report_dir
        if os.path.exists(output_dir) and os.path.isdir(output_dir):
            # 保留 results 目录
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if item != 'allure-results' and os.path.isfile(item_path):
                    os.remove(item_path)
                elif item != 'allure-results' and os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        
        if os.name == 'nt':
            cmd = f'allure generate "{results_dir}" -o "{output_dir}" --clean'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        else:
            cmd = ['allure', 'generate', results_dir, '-o', output_dir, '--clean']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, encoding='utf-8', errors='ignore')
        
        # 6. 生成 single-file 报告
        single_file_dir = os.path.join(base_dir, module_name, settings.ALLURE_SINGLE_FILE_DIR, f'execution_{execution.id}')
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
        
    except Exception as e:
        logger.error(f"Allure 报告生成失败 execution_{execution.id}: {str(e)}")
        try:
            execution.report_status = 'FAILED'
            execution.save(update_fields=['report_status'])
        except:
            pass
