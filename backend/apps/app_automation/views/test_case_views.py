# -*- coding: utf-8 -*-
"""APP测试用例管理视图"""
import os
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from loguru import logger

from ..models import AppPackage, AppTestCase, AppDevice, AppTestExecution
from ..serializers import AppPackageSerializer, AppTestCaseSerializer, AppTestExecutionSerializer


class AppPagination(PageNumberPagination):
    """APP自动化模块通用分页"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AppPackageViewSet(viewsets.ModelViewSet):
    """APP应用包名管理 ViewSet"""
    queryset = AppPackage.objects.all()
    serializer_class = AppPackageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    search_fields = ['name', 'package_name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='upload_apk', url_name='upload_apk')
    def upload_apk(self, request):
        """上传 APK 文件并提取信息"""
        if 'apk_file' not in request.FILES:
            return Response({
                'success': False,
                'message': '未找到 APK 文件'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        apk_file = request.FILES['apk_file']
        
        # 验证文件
        from ..utils.apk_parser import validate_apk_file, extract_apk_info
        from django.conf import settings
        import tempfile
        import os
        import uuid
        
        try:
            # 保存临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as tmp_file:
                for chunk in apk_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # 验证文件
            is_valid, error_msg = validate_apk_file(tmp_path)
            if not is_valid:
                os.unlink(tmp_path)
                return Response({
                    'success': False,
                    'message': f'APK 文件无效: {error_msg}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 提取信息
            apk_info = extract_apk_info(tmp_path)
            
            # 生成唯一文件名
            unique_id = str(uuid.uuid4())
            package_name = apk_info.get('package_name', 'unknown').replace('.', '_')
            filename = f"{package_name}_{unique_id}.apk"
            
            # 保存到配置目录
            packages_dir = settings.PATHS_APP_AUTOMATION_PACKAGES
            os.makedirs(packages_dir, exist_ok=True)
            final_path = os.path.join(packages_dir, filename)
            
            # 移动文件到最终位置
            import shutil
            shutil.move(tmp_path, final_path)
            
            logger.info(f"APK 文件已保存: {final_path}")
            
            if apk_info.get('package_name'):
                return Response({
                    'success': True,
                    'message': '提取成功',
                    'data': {
                        'package_name': apk_info.get('package_name', ''),
                        'app_name': apk_info.get('app_name', ''),
                        'version_name': apk_info.get('version_name', ''),
                        'version_code': apk_info.get('version_code', ''),
                        'apk_filename': filename,  # 返回文件名
                        'apk_filepath': final_path  # 返回完整路径
                    }
                })
            else:
                # 即使提取失败，也保留文件
                return Response({
                    'success': False,
                    'message': '无法从 APK 中提取包名，请手动填写',
                    'data': {
                        'apk_filename': filename,
                        'apk_filepath': final_path
                    }
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"APK 上传提取失败: {str(e)}", exc_info=True)
            # 清理临时文件
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return Response({
                'success': False,
                'message': f'处理失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def destroy(self, request, *args, **kwargs):
        """删除记录及对应的 APK 文件"""
        instance = self.get_object()
        
        # 删除关联的 APK 文件
        apk_deleted = False
        if instance.apk_filepath and os.path.exists(instance.apk_filepath):
            try:
                os.unlink(instance.apk_filepath)
                apk_deleted = True
                logger.info(f"已删除 APK 文件: {instance.apk_filepath}")
            except Exception as e:
                logger.error(f"删除 APK 文件失败: {str(e)}", exc_info=True)
        
        # 如果使用的是 FileField，也需要删除
        if instance.apk_file:
            try:
                instance.apk_file.delete(save=False)
                apk_deleted = True
                logger.info(f"已删除 FileField APK 文件: {instance.apk_file.name}")
            except Exception as e:
                logger.error(f"删除 FileField APK 文件失败: {str(e)}", exc_info=True)
        
        logger.info(f"删除应用包记录: {instance.name} ({instance.package_name})，APK 文件{'已删除' if apk_deleted else '未找到'}")
        
        return super().destroy(request, *args, **kwargs)


class AppTestCaseViewSet(viewsets.ModelViewSet):
    """APP测试用例 ViewSet"""
    queryset = AppTestCase.objects.all()
    serializer_class = AppTestCaseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['project', 'app_package']
    search_fields = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试用例"""
        test_case = self.get_object()
        device_id = request.data.get('device_id')
        package_name = request.data.get('package_name')
        
        if not device_id:
            return Response({
                'success': False,
                'message': '请选择执行设备'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 检查设备是否可用
            device = AppDevice.objects.get(device_id=device_id)
            if device.status == 'locked' and device.locked_by != request.user:
                return Response({
                    'success': False,
                    'message': '设备已被其他用户锁定'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 创建执行记录
            execution = AppTestExecution.objects.create(
                test_case=test_case,
                device=device,
                user=request.user,
                status='pending'
            )
            
            # 调用 Django-Q2 异步任务
            from django_q.tasks import async_task
            task_id = async_task(
                'apps.app_automation.tasks_async.execute_app_test_task',
                execution.id,
                package_name=package_name,
            )
            execution.task_id = task_id
            execution.save()
            
            logger.info(f"测试已提交执行: execution_id={execution.id}, task_id={task_id}")
            
            return Response({
                'success': True,
                'message': '测试已提交执行',
                'execution': AppTestExecutionSerializer(execution).data
            })
            
        except AppDevice.DoesNotExist:
            return Response({
                'success': False,
                'message': '设备不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"执行测试失败: {str(e)}", exc_info=True)
            logger.error(f"测试用例ID: {pk}, 设备ID: {device_id}, 错误类型: {type(e).__name__}")
            return Response({
                'success': False,
                'message': f'执行测试失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
