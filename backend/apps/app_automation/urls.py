# -*- coding: utf-8 -*-
from django.urls import path, include
from .views.execution_views import serve_report_file
from rest_framework.routers import DefaultRouter

from .views import (
    AppProjectViewSet,
    AppConfigViewSet,
    AppDeviceViewSet,
    AppElementViewSet,
    AppComponentViewSet,
    AppCustomComponentViewSet,
    AppComponentPackageViewSet,
    AppPackageViewSet,
    AppTestCaseViewSet,
    AppTestSuiteViewSet,
    AppNotificationLogViewSet,
    AppTestExecutionViewSet,
    AppDashboardViewSet,
)

router = DefaultRouter()

# 注册ViewSets
router.register(r'projects', AppProjectViewSet, basename='app-project')
router.register(r'config', AppConfigViewSet, basename='app-config')
router.register(r'dashboard', AppDashboardViewSet, basename='app-dashboard')
router.register(r'devices', AppDeviceViewSet, basename='app-device')
router.register(r'elements', AppElementViewSet, basename='app-element')
router.register(r'components', AppComponentViewSet, basename='app-component')
router.register(r'custom-components', AppCustomComponentViewSet, basename='app-custom-component')
router.register(r'component-packages', AppComponentPackageViewSet, basename='app-component-package')
router.register(r'packages', AppPackageViewSet, basename='app-package')
router.register(r'test-cases', AppTestCaseViewSet, basename='app-test-case')
router.register(r'test-suites', AppTestSuiteViewSet, basename='app-test-suite')
router.register(r'notification-logs', AppNotificationLogViewSet, basename='app-notification-log')
router.register(r'executions', AppTestExecutionViewSet, basename='app-execution')

# 显式添加 upload_apk 路由
from .views.test_case_views import AppPackageViewSet
upload_apk_view = AppPackageViewSet.as_view({'post': 'upload_apk'})

urlpatterns = [
    path('', include(router.urls)),
    path('packages/upload_apk/', upload_apk_view, name='app-package-upload-apk'),
    path('executions/<int:execution_id>/report/', serve_report_file, name='app-execution-report'),
    path('executions/<int:execution_id>/report/<path:file_path>', serve_report_file, name='app-execution-report-file'),
]
