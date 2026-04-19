"""
参数化数据集和执行 API 视图
"""
import csv
import io
import json
import time
import logging
import requests as http_requests

from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import (
    ApiRequest, Environment, ParameterizedDataSet, ParameterizedExecution, RequestHistory
)
from .serializers import ParameterizedDataSetSerializer, ParameterizedExecutionSerializer
from .utils import execute_assertions
from apps.core.variable_resolver import VariableResolver

logger = logging.getLogger(__name__)


class ParameterizedDataSetViewSet(viewsets.ModelViewSet):
    """参数化数据集视图"""
    queryset = ParameterizedDataSet.objects.all()
    serializer_class = ParameterizedDataSetSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ['project', 'data_type']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_file(self, request):
        """上传 CSV/Excel 文件并解析为数据集"""
        file = request.FILES.get('file')
        if not file:
            return Response({'error': '请上传文件'}, status=400)

        name = request.data.get('name', file.name)
        project_id = request.data.get('project')
        if not project_id:
            return Response({'error': '请指定项目'}, status=400)

        filename = file.name.lower()
        try:
            if filename.endswith('.csv'):
                data, variables = self._parse_csv(file)
                data_type = 'csv'
            elif filename.endswith(('.xlsx', '.xls')):
                data, variables = self._parse_excel(file)
                data_type = 'excel'
            elif filename.endswith('.json'):
                data, variables = self._parse_json(file)
                data_type = 'json'
            else:
                return Response({'error': '不支持的文件格式，请上传 CSV、Excel 或 JSON 文件'}, status=400)
        except Exception as e:
            return Response({'error': f'文件解析失败: {str(e)}'}, status=400)

        dataset = ParameterizedDataSet.objects.create(
            name=name,
            project_id=project_id,
            data_type=data_type,
            data=data,
            variables=variables,
            row_count=len(data),
            created_by=request.user,
        )

        return Response(ParameterizedDataSetSerializer(dataset).data, status=201)

    def _parse_csv(self, file):
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        data = [row for row in reader]
        variables = list(reader.fieldnames) if reader.fieldnames else []
        return data, variables

    def _parse_excel(self, file):
        import openpyxl
        wb = openpyxl.load_workbook(file, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return [], []
        headers = [str(h) if h else f'col_{i}' for i, h in enumerate(rows[0])]
        data = []
        for row in rows[1:]:
            item = {}
            for i, val in enumerate(row):
                if i < len(headers):
                    item[headers[i]] = str(val) if val is not None else ''
            data.append(item)
        return data, headers

    def _parse_json(self, file):
        content = file.read().decode('utf-8')
        parsed = json.loads(content)
        if not isinstance(parsed, list):
            raise ValueError('JSON 文件应为数组格式')
        if not parsed:
            return [], []
        if isinstance(parsed[0], dict):
            variables = list(parsed[0].keys())
        else:
            variables = ['value']
            parsed = [{'value': v} for v in parsed]
        return parsed, variables


class ParameterizedExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """参数化执行记录视图（只读）"""
    queryset = ParameterizedExecution.objects.all()
    serializer_class = ParameterizedExecutionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['request', 'test_suite', 'dataset', 'status']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'], url_path='execute')
    def execute_parameterized(self, request):
        """执行参数化测试"""
        request_id = request.data.get('request_id')
        dataset_id = request.data.get('dataset_id')
        environment_id = request.data.get('environment_id')

        if not request_id:
            return Response({'error': '请指定接口'}, status=400)
        if not dataset_id:
            return Response({'error': '请指定数据集'}, status=400)

        try:
            api_request = ApiRequest.objects.get(id=request_id)
            dataset = ParameterizedDataSet.objects.get(id=dataset_id)
        except (ApiRequest.DoesNotExist, ParameterizedDataSet.DoesNotExist) as e:
            return Response({'error': str(e)}, status=404)

        # 加载环境变量
        env_variables = {}
        global_env = Environment.objects.filter(scope='GLOBAL', is_active=True).first()
        if global_env and global_env.variables:
            for key, val in global_env.variables.items():
                env_variables[key] = val['currentValue'] if isinstance(val, dict) and 'currentValue' in val else val

        if environment_id:
            try:
                env = Environment.objects.get(id=environment_id)
                if env.variables:
                    for key, val in env.variables.items():
                        env_variables[key] = val['currentValue'] if isinstance(val, dict) and 'currentValue' in val else val
            except Environment.DoesNotExist:
                pass

        # 创建执行记录
        execution = ParameterizedExecution.objects.create(
            request=api_request,
            dataset=dataset,
            environment_id=environment_id,
            status='RUNNING',
            total_rows=dataset.row_count,
            start_time=timezone.now(),
            executed_by=request.user,
        )

        resolver = VariableResolver()
        results = []
        passed_count = 0
        failed_count = 0

        for row_idx, row_data in enumerate(dataset.data):
            try:
                # 合并环境变量和当前行数据
                variables = {**env_variables, **{k: str(v) for k, v in row_data.items()}}

                # 替换变量
                url = self._replace_variables(api_request.url or '', variables)
                url = resolver.resolve(url)

                headers = {}
                if isinstance(api_request.headers, list):
                    for h in api_request.headers:
                        if h.get('enabled', True) and h.get('key'):
                            val = self._replace_variables(str(h.get('value', '')), variables)
                            headers[h['key']] = resolver.resolve(val)
                elif isinstance(api_request.headers, dict):
                    for k, v in api_request.headers.items():
                        headers[k] = resolver.resolve(self._replace_variables(str(v), variables))

                params = {}
                if api_request.params:
                    for k, v in api_request.params.items():
                        params[k] = resolver.resolve(self._replace_variables(str(v), variables))

                body_data = None
                if api_request.body and api_request.method in ('POST', 'PUT', 'PATCH'):
                    if api_request.body.get('type') == 'json':
                        body_data = self._replace_variables_in_dict(
                            api_request.body.get('data', {}), variables
                        )

                # 执行请求
                start = time.time()
                resp = http_requests.request(
                    method=api_request.method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body_data,
                    timeout=settings.TIMEOUTS_API_REQUEST,
                )
                response_time = (time.time() - start) * 1000

                # 断言
                assertions = api_request.assertions or []
                for a in assertions:
                    if a.get('type') == 'response_time':
                        a['actual_time'] = response_time
                assertions_results = execute_assertions(resp, assertions)

                passed = all(a.get('passed', True) for a in assertions_results) if assertions_results else True

                if passed:
                    passed_count += 1
                else:
                    failed_count += 1

                results.append({
                    'row': row_idx,
                    'data': row_data,
                    'status_code': resp.status_code,
                    'response_time': round(response_time, 1),
                    'passed': passed,
                    'assertions_results': assertions_results,
                })

            except Exception as e:
                failed_count += 1
                results.append({
                    'row': row_idx,
                    'data': row_data,
                    'passed': False,
                    'error': str(e),
                })

        # 更新执行记录
        execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
        execution.passed_rows = passed_count
        execution.failed_rows = failed_count
        execution.results = results
        execution.end_time = timezone.now()
        execution.save()

        return Response(ParameterizedExecutionSerializer(execution).data)

    def _replace_variables(self, text, variables):
        import re
        def replacer(match):
            key = match.group(1).strip()
            return str(variables.get(key, match.group(0)))
        return re.sub(r'\{\{(.+?)\}\}', replacer, str(text))

    def _replace_variables_in_dict(self, data, variables):
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        return data
