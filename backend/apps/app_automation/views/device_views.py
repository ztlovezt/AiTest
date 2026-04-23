# -*- coding: utf-8 -*-
"""APP 设备管理视图。"""
import base64
import logging
import subprocess

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .test_case_views import AppPagination
from ..managers.device_manager import DeviceManager
from ..models import AppDevice, AppPackage
from ..serializers import AppDeviceSerializer
from ..utils.performance_sampler import performance_sampler

logger = logging.getLogger(__name__)


def get_adb_path() -> str:
    """Get configured adb path."""
    try:
        from ..models import AppTestConfig
        config = AppTestConfig.objects.first()
        return config.adb_path if config else 'adb'
    except Exception as exc:
        logger.warning(f'Failed to get adb config, fallback to default adb: {exc}')
        return 'adb'


def safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class AppDeviceViewSet(viewsets.ModelViewSet):
    """APP 设备管理 ViewSet。"""

    queryset = AppDevice.objects.all()
    serializer_class = AppDeviceSerializer
    # Support adb device ids like `127.0.0.1:7555` in router detail/action URLs.
    lookup_value_regex = r'\d+'
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'connection_type']
    search_fields = ['device_id', 'name']

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_field or 'pk')
        queryset = self.filter_queryset(self.get_queryset())

        device = queryset.filter(pk=lookup_value).first()
        if device is None:
            from django.http import Http404
            raise Http404

        self.check_object_permissions(self.request, device)
        return device

    def _get_manager(self) -> DeviceManager:
        return DeviceManager(adb_path=get_adb_path())

    def _resolve_package_name(self, request) -> str:
        package_name = str(request.data.get('package_name', '')).strip()
        package_id = request.data.get('package_id')
        if package_name:
            return package_name
        if package_id:
            package = AppPackage.objects.filter(id=package_id).first()
            if package:
                return package.package_name
        return ''

    def _resolve_apk_path(self, request) -> str:
        apk_path = str(request.data.get('apk_filepath', '')).strip()
        package_id = request.data.get('package_id')
        if apk_path:
            return apk_path
        if package_id:
            package = AppPackage.objects.filter(id=package_id).first()
            if package:
                if package.apk_filepath:
                    return package.apk_filepath
                if package.apk_file:
                    return package.apk_file.path
        return ''

    def _resolve_package_name_from_request(self, request) -> str:
        package_name = str(request.query_params.get('package_name', '')).strip()
        if package_name:
            return package_name
        return self._resolve_package_name(request)

    @action(detail=False, methods=['get'])
    def discover(self, request):
        """Discover adb devices and refresh stored status."""
        try:
            manager = self._get_manager()
            devices_info = manager.list_devices()
            connected_device_ids = [info['device_id'] for info in devices_info]
            db_devices = []

            for device_info in devices_info:
                device_id = device_info['device_id']
                if ':' in device_id:
                    connection_type = 'remote_emulator'
                    ip_address = device_info.get('ip_address') or ''
                elif device_id.startswith('emulator-'):
                    connection_type = 'emulator'
                    ip_address = '127.0.0.1'
                else:
                    connection_type = 'usb'
                    ip_address = device_info.get('ip_address') or ''

                current_status = device_info.get('status') or 'offline'
                defaults = {
                    'name': device_info.get('name') or '',
                    'android_version': device_info.get('android_version') or '',
                    'ip_address': ip_address,
                    'port': device_info.get('port') or 5555,
                    'connection_type': connection_type,
                }

                existing_device = AppDevice.objects.filter(device_id=device_id).first()
                if current_status == 'online':
                    if existing_device and existing_device.status == 'locked':
                        defaults['status'] = 'locked'
                    else:
                        defaults['status'] = 'available'
                else:
                    defaults['status'] = 'offline'

                device = existing_device
                if device and device.status == 'locked' and current_status == 'online':
                    defaults['status'] = 'locked'

                device, _ = AppDevice.objects.update_or_create(device_id=device_id, defaults=defaults)
                db_devices.append(device)

            offline_devices = AppDevice.objects.exclude(device_id__in=connected_device_ids)
            offline_count = 0
            for device in offline_devices:
                if device.status != 'locked':
                    device.status = 'offline'
                    device.save(update_fields=['status', 'updated_at'])
                    offline_count += 1

            all_devices = AppDevice.objects.all().order_by('-updated_at')

            return Response({
                'success': True,
                'message': f'发现 {len(db_devices)} 个在线设备，{offline_count} 个设备标记为离线',
                'devices': AppDeviceSerializer(all_devices, many=True).data,
            })
        except Exception as exc:
            logger.error(f'发现设备失败: {exc}', exc_info=True)
            return Response({
                'success': False,
                'message': f'发现设备失败: {exc}',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        device = self.get_object()
        if device.status == 'locked':
            return Response({'success': False, 'message': '设备已被锁定'}, status=status.HTTP_400_BAD_REQUEST)
        device.lock(request.user)
        return Response({
            'success': True,
            'message': '设备锁定成功',
            'device': AppDeviceSerializer(device).data,
        })

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        device = self.get_object()
        if device.locked_by and device.locked_by != request.user:
            return Response({'success': False, 'message': '无权解锁他人锁定的设备'}, status=status.HTTP_403_FORBIDDEN)
        device.unlock()
        return Response({
            'success': True,
            'message': '设备解锁成功',
            'device': AppDeviceSerializer(device).data,
        })

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        device = self.get_object()
        if device.connection_type not in ['remote', 'remote_emulator']:
            return Response({'success': False, 'message': '只能断开远程设备连接'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            manager = self._get_manager()
            success = manager.disconnect_device(f'{device.ip_address}:{device.port}')
            if not success:
                return Response({'success': False, 'message': '断开设备失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            device.status = 'offline'
            device.save(update_fields=['status', 'updated_at'])
            return Response({
                'success': True,
                'message': f'设备 {device.name or device.device_id} 已断开连接',
                'device': AppDeviceSerializer(device).data,
            })
        except Exception as exc:
            return Response({'success': False, 'message': f'断开设备失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def connect(self, request):
        try:
            ip_address = request.data.get('ip_address')
            port = request.data.get('port', 5555)
            if not ip_address:
                return Response({'success': False, 'message': '请提供设备 IP 地址'}, status=status.HTTP_400_BAD_REQUEST)

            manager = self._get_manager()
            device_info = manager.connect_device(ip_address, port)
            device, _ = AppDevice.objects.update_or_create(
                device_id=device_info['device_id'],
                defaults={
                    'name': device_info.get('name') or '',
                    'status': 'online',
                    'android_version': device_info.get('android_version', ''),
                    'ip_address': ip_address,
                    'port': port,
                    'connection_type': 'remote_emulator',
                },
            )
            return Response({
                'success': True,
                'message': '设备连接成功',
                'device': AppDeviceSerializer(device).data,
            })
        except Exception as exc:
            logger.error(f'连接设备失败: {exc}')
            return Response({'success': False, 'message': f'连接设备失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='screenshot')
    def screenshot(self, request, pk=None):
        """Capture current device screenshot and return a data URL."""
        device = self.get_object()
        if device.status == 'offline':
            return Response({'code': 400, 'msg': '设备离线，无法截图', 'success': False}, status=status.HTTP_400_BAD_REQUEST)

        try:
            adb_path = get_adb_path()
            result = subprocess.run(
                [adb_path, '-s', device.device_id, 'exec-out', 'screencap', '-p'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                timeout=10,
            )
            if not result.stdout:
                return Response({'code': 500, 'msg': '截图失败：无返回数据', 'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            image_base64 = base64.b64encode(result.stdout).decode('utf-8')
            logger.info(f'设备 {device.device_id} 截图成功')
            return Response({
                'code': 0,
                'msg': '截图成功',
                'success': True,
                'data': {
                    'filename': f'device_{device.id}_{int(timezone.now().timestamp())}.png',
                    'content': f'data:image/png;base64,{image_base64}',
                    'device_id': device.device_id,
                    'timestamp': int(timezone.now().timestamp()),
                },
            })
        except subprocess.TimeoutExpired:
            logger.error(f'设备 {device.device_id} 截图超时')
            return Response({'code': 500, 'msg': '截图超时，请检查设备连接', 'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            logger.error(f'设备 {device.device_id} 截图失败: {exc}')
            return Response({'code': 500, 'msg': f'截图失败: {exc}', 'success': False}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='current-app')
    def current_app(self, request, pk=None):
        """Get current foreground app."""
        device = self.get_object()
        try:
            app_info = self._get_manager().get_current_app(device.device_id)
            return Response({'success': True, 'data': app_info})
        except Exception as exc:
            logger.error(f'获取前台应用失败: {exc}')
            return Response({'success': False, 'message': f'获取前台应用失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='installed-packages')
    def installed_packages(self, request, pk=None):
        """List installed third-party packages on the device."""
        device = self.get_object()
        try:
            packages = self._get_manager().get_installed_packages(device.device_id)
            return Response({'success': True, 'data': packages})
        except Exception as exc:
            logger.error(f'获取已安装应用失败: {exc}')
            return Response({'success': False, 'message': f'获取已安装应用失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='performance/device')
    def performance_device(self, request, pk=None):
        """Get a device-level performance snapshot."""
        device = self.get_object()
        try:
            data = performance_sampler.get_device_snapshot(self._get_manager(), device.device_id)
            return Response({'success': True, 'data': data})
        except Exception as exc:
            logger.error(f'获取设备性能失败: {exc}')
            return Response({'success': False, 'message': f'获取设备性能失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='performance/app')
    def performance_app(self, request, pk=None):
        """Get an app-level performance snapshot."""
        device = self.get_object()
        package_name = self._resolve_package_name_from_request(request)
        if not package_name:
            return Response({'success': False, 'message': '缺少应用包名'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = performance_sampler.get_app_snapshot(self._get_manager(), device.device_id, package_name)
            return Response({'success': True, 'data': data})
        except Exception as exc:
            logger.error(f'获取应用性能失败: {exc}')
            return Response({'success': False, 'message': f'获取应用性能失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='performance/reset')
    def performance_reset(self, request, pk=None):
        """Reset performance sampler caches for the device/package."""
        device = self.get_object()
        package_name = self._resolve_package_name(request)
        performance_sampler.reset(device.device_id, package_name=package_name or None)
        return Response({'success': True, 'message': '性能采样缓存已重置'})

    @action(detail=True, methods=['get'], url_path='logcat')
    def logcat(self, request, pk=None):
        """Read recent device or app logcat lines."""
        device = self.get_object()
        scope = str(request.query_params.get('scope', 'device')).strip() or 'device'
        level = str(request.query_params.get('level', '')).strip()
        keyword = str(request.query_params.get('keyword', '')).strip()
        lines = min(max(safe_int(request.query_params.get('lines', 200) or 200, 200), 50), 1000)
        package_name = self._resolve_package_name_from_request(request)

        try:
            data = performance_sampler.get_logcat(
                self._get_manager(),
                device.device_id,
                lines=lines,
                scope=scope,
                package_name=package_name,
                level=level,
                keyword=keyword,
            )
            return Response({'success': True, 'data': data})
        except Exception as exc:
            logger.error(f'获取设备日志失败: {exc}')
            return Response({'success': False, 'message': f'获取设备日志失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='logcat/clear')
    def clear_logcat(self, request, pk=None):
        """Clear device logcat buffer."""
        device = self.get_object()
        try:
            self._get_manager().clear_logcat(device.device_id)
            return Response({'success': True, 'message': '设备日志已清空'})
        except Exception as exc:
            logger.error(f'清空设备日志失败: {exc}')
            return Response({'success': False, 'message': f'清空设备日志失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='install-apk')
    def install_apk(self, request, pk=None):
        """Install an APK to the current device."""
        device = self.get_object()
        apk_path = self._resolve_apk_path(request)
        if not apk_path:
            return Response({'success': False, 'message': '缺少 APK 文件路径或应用包选择'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = self._get_manager().install_apk(device.device_id, apk_path, replace=True)
            return Response({'success': True, 'message': '应用安装成功', 'data': {'output': output, 'apk_path': apk_path}})
        except Exception as exc:
            logger.error(f'安装 APK 失败: {exc}')
            return Response({'success': False, 'message': f'安装 APK 失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='launch-app')
    def launch_app(self, request, pk=None):
        device = self.get_object()
        package_name = self._resolve_package_name(request)
        activity = str(request.data.get('activity', '')).strip()
        if not package_name:
            return Response({'success': False, 'message': '缺少应用包名'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = self._get_manager().launch_app(device.device_id, package_name, activity=activity)
            return Response({'success': True, 'message': '应用启动成功', 'data': {'output': output, 'package_name': package_name}})
        except Exception as exc:
            logger.error(f'启动应用失败: {exc}')
            return Response({'success': False, 'message': f'启动应用失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='stop-app')
    def stop_app(self, request, pk=None):
        device = self.get_object()
        package_name = self._resolve_package_name(request)
        if not package_name:
            return Response({'success': False, 'message': '缺少应用包名'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = self._get_manager().stop_app(device.device_id, package_name)
            return Response({'success': True, 'message': '应用已停止', 'data': {'output': output, 'package_name': package_name}})
        except Exception as exc:
            logger.error(f'停止应用失败: {exc}')
            return Response({'success': False, 'message': f'停止应用失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='clear-app-data')
    def clear_app_data(self, request, pk=None):
        device = self.get_object()
        package_name = self._resolve_package_name(request)
        if not package_name:
            return Response({'success': False, 'message': '缺少应用包名'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = self._get_manager().clear_app_data(device.device_id, package_name)
            return Response({'success': True, 'message': '应用数据已清理', 'data': {'output': output, 'package_name': package_name}})
        except Exception as exc:
            logger.error(f'清理应用数据失败: {exc}')
            return Response({'success': False, 'message': f'清理应用数据失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='uninstall-app')
    def uninstall_app(self, request, pk=None):
        device = self.get_object()
        package_name = self._resolve_package_name(request)
        if not package_name:
            return Response({'success': False, 'message': '缺少应用包名'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            output = self._get_manager().uninstall_app(device.device_id, package_name)
            return Response({'success': True, 'message': '应用卸载成功', 'data': {'output': output, 'package_name': package_name}})
        except Exception as exc:
            logger.error(f'卸载应用失败: {exc}')
            return Response({'success': False, 'message': f'卸载应用失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
