# -*- coding: utf-8 -*-
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from .views import (
    AppComponentPackageViewSet,
    AppComponentViewSet,
    AppConfigViewSet,
    AppCustomComponentViewSet,
    AppDashboardViewSet,
    AppDeviceViewSet,
    AppElementViewSet,
    AppNotificationLogViewSet,
    AppPackageViewSet,
    AppProjectViewSet,
    AppTestCaseViewSet,
    AppTestExecutionViewSet,
    AppTestSuiteViewSet,
)
from .views.execution_views import serve_report_file
from .views.test_case_views import AppPackageViewSet as UploadPackageViewSet

router = DefaultRouter()

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

upload_apk_view = UploadPackageViewSet.as_view({'post': 'upload_apk'})
device_screenshot_view = AppDeviceViewSet.as_view({'post': 'screenshot'})
device_current_app_view = AppDeviceViewSet.as_view({'get': 'current_app'})
device_installed_packages_view = AppDeviceViewSet.as_view({'get': 'installed_packages'})
device_performance_device_view = AppDeviceViewSet.as_view({'get': 'performance_device'})
device_performance_app_view = AppDeviceViewSet.as_view({'get': 'performance_app'})
device_performance_reset_view = AppDeviceViewSet.as_view({'post': 'performance_reset'})
device_logcat_view = AppDeviceViewSet.as_view({'get': 'logcat'})
device_clear_logcat_view = AppDeviceViewSet.as_view({'post': 'clear_logcat'})
device_install_apk_view = AppDeviceViewSet.as_view({'post': 'install_apk'})
device_launch_app_view = AppDeviceViewSet.as_view({'post': 'launch_app'})
device_stop_app_view = AppDeviceViewSet.as_view({'post': 'stop_app'})
device_clear_app_data_view = AppDeviceViewSet.as_view({'post': 'clear_app_data'})
device_uninstall_app_view = AppDeviceViewSet.as_view({'post': 'uninstall_app'})

urlpatterns = [
    # Explicit device action routes to support adb ids like `127.0.0.1:7555`.
    re_path(r'^devices/(?P<pk>\d+)/screenshot/$', device_screenshot_view, name='app-device-screenshot'),
    re_path(r'^devices/(?P<pk>\d+)/current-app/$', device_current_app_view, name='app-device-current-app'),
    re_path(r'^devices/(?P<pk>\d+)/installed-packages/$', device_installed_packages_view, name='app-device-installed-packages'),
    re_path(r'^devices/(?P<pk>\d+)/performance/device/$', device_performance_device_view, name='app-device-performance-device'),
    re_path(r'^devices/(?P<pk>\d+)/performance/app/$', device_performance_app_view, name='app-device-performance-app'),
    re_path(r'^devices/(?P<pk>\d+)/performance/reset/$', device_performance_reset_view, name='app-device-performance-reset'),
    re_path(r'^devices/(?P<pk>\d+)/logcat/$', device_logcat_view, name='app-device-logcat'),
    re_path(r'^devices/(?P<pk>\d+)/logcat/clear/$', device_clear_logcat_view, name='app-device-clear-logcat'),
    re_path(r'^devices/(?P<pk>\d+)/install-apk/$', device_install_apk_view, name='app-device-install-apk'),
    re_path(r'^devices/(?P<pk>\d+)/launch-app/$', device_launch_app_view, name='app-device-launch-app'),
    re_path(r'^devices/(?P<pk>\d+)/stop-app/$', device_stop_app_view, name='app-device-stop-app'),
    re_path(r'^devices/(?P<pk>\d+)/clear-app-data/$', device_clear_app_data_view, name='app-device-clear-app-data'),
    re_path(r'^devices/(?P<pk>\d+)/uninstall-app/$', device_uninstall_app_view, name='app-device-uninstall-app'),
    path('', include(router.urls)),
    path('packages/upload_apk/', upload_apk_view, name='app-package-upload-apk'),
    path('executions/<int:execution_id>/report/', serve_report_file, name='app-execution-report'),
    path('executions/<int:execution_id>/report/<path:file_path>', serve_report_file, name='app-execution-report-file'),
]
