"""
导入导出 API 视图
"""
import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import JsonResponse

from ..models import ApiProject, ApiCollection, ApiRequest
from . import OpenAPIParser, PostmanParser, CurlParser, HARParser, OpenAPIExporter, PostmanExporter

logger = logging.getLogger(__name__)


class ImportPreviewView(APIView):
    """导入预览 - 解析文件并返回待导入的接口列表"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        format_type = request.data.get('format', '')
        content = ''

        if format_type == 'curl':
            content = request.data.get('content', '')
            if not content:
                return Response({'error': '请输入 cURL 命令'}, status=400)
        else:
            file = request.FILES.get('file')
            if not file:
                return Response({'error': '请上传文件'}, status=400)
            raw_bytes = file.read()
            try:
                content = raw_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                content = raw_bytes.decode('utf-8', errors='ignore')

        parser_map = {
            'openapi': OpenAPIParser,
            'swagger': OpenAPIParser,
            'postman': PostmanParser,
            'curl': CurlParser,
            'har': HARParser,
        }

        parser_cls = parser_map.get(format_type)
        if not parser_cls:
            return Response({'error': f'不支持的格式: {format_type}'}, status=400)

        try:
            parser = parser_cls()
            result = parser.parse(content, filename=getattr(file, 'name', '') if format_type != 'curl' else '')
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        except Exception as e:
            logger.exception(f'Import preview failed: {e}')
            return Response({'error': f'解析失败: {str(e)}'}, status=500)


class ImportConfirmView(APIView):
    """确认导入 - 将解析结果写入数据库"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        project_id = request.data.get('project_id')
        collections_data = request.data.get('collections', [])

        if not project_id:
            return Response({'error': '请选择目标项目'}, status=400)

        try:
            project = ApiProject.objects.get(id=project_id)
        except ApiProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=404)

        created_collections = 0
        created_requests = 0

        try:
            for col_data in collections_data:
                # 创建集合
                collection = ApiCollection.objects.create(
                    name=col_data.get('name', 'Imported'),
                    description=col_data.get('description', ''),
                    project=project,
                )
                created_collections += 1

                # 创建请求
                for idx, req_data in enumerate(col_data.get('requests', [])):
                    headers = req_data.get('headers', [])
                    if isinstance(headers, dict):
                        headers = [{'key': k, 'value': v, 'enabled': True} for k, v in headers.items()]

                    params = req_data.get('params', {})
                    body = req_data.get('body', {})

                    ApiRequest.objects.create(
                        collection=collection,
                        name=req_data.get('name', f'Request {idx + 1}')[:200],
                        description=req_data.get('description', ''),
                        method=req_data.get('method', 'GET').upper(),
                        url=req_data.get('url', ''),
                        headers=headers,
                        params=params,
                        body=body,
                        order=idx,
                        created_by=request.user,
                    )
                    created_requests += 1

            return Response({
                'message': f'导入成功：{created_collections} 个集合，{created_requests} 个接口',
                'created_collections': created_collections,
                'created_requests': created_requests,
            })

        except Exception as e:
            logger.exception(f'Import confirm failed: {e}')
            return Response({'error': f'导入失败: {str(e)}'}, status=500)


class ExportView(APIView):
    """导出项目接口"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        format_type = request.query_params.get('format', 'openapi')

        try:
            project = ApiProject.objects.get(id=project_id)
        except ApiProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=404)

        collections = ApiCollection.objects.filter(project=project).order_by('order')
        requests = ApiRequest.objects.filter(
            collection__project=project
        ).select_related('collection').order_by('collection__order', 'order')

        if format_type == 'openapi':
            exporter = OpenAPIExporter()
            result = exporter.export(project, collections, requests)
            response = JsonResponse(result, json_dumps_params={'ensure_ascii': False, 'indent': 2})
            response['Content-Disposition'] = f'attachment; filename="{project.name}_openapi.json"'
            return response
        elif format_type == 'postman':
            exporter = PostmanExporter()
            result = exporter.export(project, collections, requests)
            response = JsonResponse(result, json_dumps_params={'ensure_ascii': False, 'indent': 2})
            response['Content-Disposition'] = f'attachment; filename="{project.name}_postman.json"'
            return response
        else:
            return Response({'error': f'不支持的导出格式: {format_type}'}, status=400)
