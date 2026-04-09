"""
变量提取器
从 HTTP 响应中提取值，存入上下文变量池
"""
import re
import json
import logging

logger = logging.getLogger(__name__)


def extract_variables(response, extractors):
    """
    从响应中执行所有提取器，返回提取的变量和详情
    Args:
        response: requests.Response 对象
        extractors: 提取器配置列表
            [
                {
                    "variable_name": "auth_token",
                    "source": "body",           # body / header / cookie / status_code
                    "extract_type": "json_path", # json_path / regex / header_key
                    "expression": "$.data.token",
                    "default_value": ""
                }
            ]
    Returns:
        tuple: (extracted_vars: dict, details: list)
            extracted_vars: {"auth_token": "xxx", ...}
            details: [{"variable_name": "auth_token", "value": "xxx", "success": True}, ...]
    """
    extracted_vars = {}
    details = []

    if not extractors or not isinstance(extractors, list):
        return extracted_vars, details

    for extractor in extractors:
        if not isinstance(extractor, dict):
            continue

        variable_name = extractor.get('variable_name', '').strip()
        if not variable_name:
            continue

        try:
            value = _extract_single(response, extractor)
            extracted_vars[variable_name] = value
            details.append({
                'variable_name': variable_name,
                'value': value if not isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False),
                'success': True,
                'source': extractor.get('source', ''),
                'expression': extractor.get('expression', ''),
            })
        except Exception as e:
            default = extractor.get('default_value', '')
            extracted_vars[variable_name] = default
            details.append({
                'variable_name': variable_name,
                'value': default,
                'success': False,
                'error': str(e),
                'source': extractor.get('source', ''),
                'expression': extractor.get('expression', ''),
            })

    return extracted_vars, details


def _extract_single(response, extractor):
    """执行单个提取器"""
    source = extractor.get('source', 'body')
    extract_type = extractor.get('extract_type', 'json_path')
    expression = extractor.get('expression', '')
    default_value = extractor.get('default_value', '')

    if source == 'body':
        if extract_type == 'json_path':
            return _extract_json_path(response, expression, default_value)
        elif extract_type == 'regex':
            return _extract_regex(response.text, expression, default_value)
        else:
            return default_value

    elif source == 'header':
        header_value = response.headers.get(expression, None)
        if header_value is None:
            # 不区分大小写查找
            for key, val in response.headers.items():
                if key.lower() == expression.lower():
                    return val
            return default_value
        return header_value

    elif source == 'cookie':
        return response.cookies.get(expression, default_value)

    elif source == 'status_code':
        return str(response.status_code)

    elif source == 'response_time':
        return str(int(response.elapsed.total_seconds() * 1000))

    return default_value


def _extract_json_path(response, expression, default_value):
    """JSONPath 提取"""
    try:
        data = response.json()
    except (json.JSONDecodeError, ValueError):
        raise ValueError('响应体不是有效的 JSON 格式')

    # 尝试使用 jsonpath_ng
    try:
        from jsonpath_ng import parse as jp_parse
        matches = jp_parse(expression).find(data)
        if matches:
            return matches[0].value
        return default_value
    except ImportError:
        pass

    # 简单的点路径提取作为回退
    return _simple_path_extract(data, expression, default_value)


def _simple_path_extract(data, expression, default_value):
    """
    简单的路径提取，支持 $.key.subkey[0].field 格式
    """
    if not expression:
        return default_value

    # 去掉 $. 前缀
    path = expression
    if path.startswith('$.'):
        path = path[2:]
    elif path.startswith('$'):
        path = path[1:]

    current = data
    # 分割路径：支持 key[0].subkey 格式
    parts = re.split(r'\.(?![^\[]*\])', path)

    for part in parts:
        if not part:
            continue

        # 处理数组索引 key[0]
        match = re.match(r'^(\w+)\[(\d+)\]$', part)
        if match:
            key, index = match.group(1), int(match.group(2))
            if isinstance(current, dict) and key in current:
                current = current[key]
                if isinstance(current, list) and index < len(current):
                    current = current[index]
                else:
                    return default_value
            else:
                return default_value
        elif re.match(r'^\[(\d+)\]$', part):
            # 纯数组索引 [0]
            index = int(part[1:-1])
            if isinstance(current, list) and index < len(current):
                current = current[index]
            else:
                return default_value
        else:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default_value

    return current


def _extract_regex(text, expression, default_value):
    """正则表达式提取"""
    if not expression:
        return default_value

    match = re.search(expression, text)
    if match:
        # 优先返回第一个捕获组
        if match.groups():
            return match.group(1)
        return match.group(0)
    return default_value
