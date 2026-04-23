import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from django.utils import timezone

from .models import AppDevice, DeviceStatus
from .scrcpy_service import scrcpy_service

logger = logging.getLogger(__name__)


class AppExecutionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
            self.group_name = f"app_execution_{self.execution_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket connected: execution_id={self.execution_id}")
        except Exception as exc:
            logger.error(f"WebSocket connect failed: {exc}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "group_name"):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(f"WebSocket disconnected: execution_id={self.execution_id}, code={close_code}")
        except Exception as exc:
            logger.error(f"WebSocket disconnect failed: {exc}")

    async def execution_update(self, event):
        try:
            await self.send_json(event)
        except Exception as exc:
            logger.error(f"WebSocket push failed: {exc}")


class RemoteDeviceConsumer(AsyncWebsocketConsumer):
    """Remote device control consumer using AppDevice primary key."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_pk = None
        self.device_id = None
        self.user = None
        self.session_start_time = None

    async def connect(self):
        try:
            self.device_pk = self.scope["url_route"]["kwargs"]["id"]
            self.user = self.scope["user"]

            if not self.user.is_authenticated:
                logger.warning(f"Anonymous user attempted device websocket connect: id={self.device_pk}")
                await self.close()
                return

            logger.info(f"WebSocket connect request: id={self.device_pk}, user={self.user.username}")

            device = await self.get_device(self.device_pk)
            if not device:
                logger.error(f"Device not found: id={self.device_pk}")
                await self.close()
                return

            self.device_id = device.device_id
            await self.lock_device(device)
            await self.accept()
            self.session_start_time = timezone.now()

            logger.info(f"WebSocket connected: id={self.device_pk}, adb_device_id={self.device_id}")
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "connected",
                        "message": "连接成功",
                        "device_id": device.pk,
                    }
                )
            )

            await self.start_scrcpy_session()
        except Exception as exc:
            logger.error(f"WebSocket connect failed: {exc}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        try:
            logger.info(f"WebSocket disconnected: id={self.device_pk}, adb_device_id={self.device_id}, code={close_code}")
            if self.device_id:
                scrcpy_service.stop_session(self.device_id)
            if self.device_pk:
                await self.unlock_device(self.device_pk)
        except Exception as exc:
            logger.error(f"WebSocket disconnect failed: {exc}")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if bytes_data:
                if self.device_id and scrcpy_service.is_session_active(self.device_id):
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: scrcpy_service.send_control(self.device_id, bytes_data),
                    )
            elif text_data:
                data = json.loads(text_data)
                logger.info(f"Received websocket text command: {data}")
        except Exception as exc:
            logger.error(f"Receive failed: {exc}")

    async def start_scrcpy_session(self):
        try:
            loop = asyncio.get_event_loop()

            def video_callback(data):
                try:
                    loop.call_soon_threadsafe(
                        lambda: asyncio.ensure_future(self.send(bytes_data=data))
                    )
                except Exception as exc:
                    logger.error(f"Send video frame failed: {exc}")

            executor = ThreadPoolExecutor(max_workers=1)
            result = await loop.run_in_executor(
                executor,
                lambda: scrcpy_service.start_session(self.device_id, video_callback),
            )

            if not result:
                logger.error(f"Start scrcpy session failed: adb_device_id={self.device_id}")
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "error",
                            "message": "启动设备会话失败",
                        }
                    )
                )
            else:
                logger.info(f"Scrcpy session started: adb_device_id={self.device_id}")
        except Exception as exc:
            logger.error(f"Start scrcpy session exception: {exc}", exc_info=True)
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": f"启动失败: {str(exc)}",
                    }
                )
            )

    async def send_video_frame(self, data: bytes):
        try:
            await self.send(bytes_data=data)
        except Exception as exc:
            logger.error(f"Send video frame exception: {exc}")

    @database_sync_to_async
    def get_device(self, device_pk):
        try:
            return AppDevice.objects.get(pk=int(device_pk))
        except (AppDevice.DoesNotExist, TypeError, ValueError):
            return None

    @database_sync_to_async
    def lock_device(self, device):
        device.lock(self.user)
        device.status = DeviceStatus.LOCKED
        device.save()
        logger.info(f"Device locked: id={device.pk}, adb_device_id={device.device_id}, user={self.user.username}")

    @database_sync_to_async
    def unlock_device(self, device_pk):
        try:
            device = AppDevice.objects.get(pk=int(device_pk))
            device.unlock()
            device.status = DeviceStatus.AVAILABLE
            device.save()
            logger.info(f"Device unlocked: id={device.pk}, adb_device_id={device.device_id}")
        except (AppDevice.DoesNotExist, TypeError, ValueError):
            logger.warning(f"Device not found while unlocking: id={device_pk}")
