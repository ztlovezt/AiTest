# -*- coding: utf-8 -*-
"""APP自动化定时任务视图"""
import json
import logging

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from .test_case_views import AppPagination
from ..models import (
    AppScheduledTask, AppNotificationLog,
    AppTestSuite, AppTestCase, AppDevice,
)
from ..serializers import (
    AppScheduledTaskSerializer,
    AppNotificationLogSerializer,
)

logger = logging.getLogger(__name__)


class AppScheduledTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """
    APP定时任务视图集（已弃用）
    
    此视图集已弃用，请使用新的统一调度器API：
    - API路径: /api/scheduler/schedules/
    - 文档: 请参考 scheduler 应用
    
    此视图集仅保留只读功能，用于查看历史任务。
    新任务请通过统一调度器创建。
    """
    queryset = AppScheduledTask.objects.all()
    serializer_class = AppScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task_type', 'status', 'trigger_type', 'project']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'next_run_time', 'last_run_time']
    ordering = ['-created_at']

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data['deprecated'] = True
        response.data['message'] = '此API已弃用，请使用 /api/scheduler/schedules/ 创建新任务'
        return response
    
    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data['deprecated'] = True
        response.data['message'] = '此API已弃用，请使用 /api/scheduler/schedules/ 创建新任务'
        return response
    
    def create(self, request, *args, **kwargs):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/ 创建新任务'},
            status=status.HTTP_410_GONE
        )
    
    def update(self, request, *args, **kwargs):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/ 更新任务'},
            status=status.HTTP_410_GONE
        )
    
    def destroy(self, request, *args, **kwargs):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/ 删除任务'},
            status=status.HTTP_410_GONE
        )

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/{id}/toggle/ 暂停任务'},
            status=status.HTTP_410_GONE
        )

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/{id}/toggle/ 恢复任务'},
            status=status.HTTP_410_GONE
        )

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        return Response(
            {'error': '此API已弃用，请使用 /api/scheduler/schedules/{id}/execute/ 执行任务'},
            status=status.HTTP_410_GONE
        )


class AppNotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """APP通知日志视图集（只读）"""
    queryset = AppNotificationLog.objects.all()
    serializer_class = AppNotificationLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type']
    search_fields = ['task_name', 'notification_content']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        log = self.get_object()
        if log.status == 'failed':
            log.retry_count += 1
            log.is_retried = True
            log.save(update_fields=['retry_count', 'is_retried'])
            return Response({'success': True, 'message': '通知已加入重试队列'})
        return Response({'success': False, 'message': '只能重试失败的通知'},
                        status=status.HTTP_400_BAD_REQUEST)
