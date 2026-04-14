import logging
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .scrcpy_service import scrcpy_service
from .models import AppDevice, DeviceStatus
from django.utils import timezone
import asyncio

logger = logging.getLogger(__name__)


class AppExecutionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
            self.group_name = f"app_execution_{self.execution_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket 连接成功: execution_id={self.execution_id}")
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(f"WebSocket 断开: execution_id={self.execution_id}, code={close_code}")
        except Exception as e:
            logger.error(f"WebSocket 断开处理失败: {e}")

    async def execution_update(self, event):
        try:
            await self.send_json(event)
        except Exception as e:
            logger.error(f"WebSocket 推送消息失败: {e}")


class RemoteDeviceConsumer(AsyncWebsocketConsumer):
    """远程设备控制 WebSocket Consumer"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_id = None
        self.user = None
        self.session_start_time = None
    
    async def connect(self):
        try:
            # 从 URL 获取 device_id
            self.device_id = self.scope["url_route"]["kwargs"]["device_id"]
            self.user = self.scope["user"]
            
            if not self.user.is_authenticated:
                logger.warning(f"未认证用户尝试连接设备 {self.device_id}")
                await self.close()
                return
            
            logger.info(f"WebSocket 连接请求: device_id={self.device_id}, user={self.user.username}")
            
            # 检查设备是否存在
            device = await self.get_device(self.device_id)
            if not device:
                logger.error(f"设备不存在: {self.device_id}")
                await self.close()
                return
            
            # 锁定设备
            await self.lock_device(device)
            
            # 接受连接
            await self.accept()
            self.session_start_time = timezone.now()
            
            logger.info(f"WebSocket 连接成功: device_id={self.device_id}")
            
            # 发送连接成功消息
            await self.send(text_data=json.dumps({
                'type': 'connected',
                'message': '连接成功',
                'device_id': self.device_id
            }))
            
            # 启动 scrcpy 会话
            await self.start_scrcpy_session()
            
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}", exc_info=True)
            await self.close()
    
    async def disconnect(self, close_code):
        try:
            logger.info(f"WebSocket 断开: device_id={self.device_id}, code={close_code}")
            
            # 停止 scrcpy 会话
            if self.device_id:
                scrcpy_service.stop_session(self.device_id)
            
            # 解锁设备
            if self.device_id:
                await self.unlock_device(self.device_id)
            
        except Exception as e:
            logger.error(f"WebSocket 断开处理失败: {e}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """接收前端发来的控制命令"""
        try:
            if bytes_data:
                # 二进制数据是控制命令 - 使用线程池异步发送，避免阻塞事件循环
                if self.device_id and scrcpy_service.is_session_active(self.device_id):
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: scrcpy_service.send_control(self.device_id, bytes_data)
                    )
            elif text_data:
                # 文本数据可能是其他指令
                data = json.loads(text_data)
                logger.info(f"收到文本指令: {data}")
                
        except Exception as e:
            logger.error(f"接收数据失败: {e}")
    
    async def start_scrcpy_session(self):
        """启动 scrcpy 会话"""
        try:
            # 获取当前事件循环，用于从后台线程调度协程
            loop = asyncio.get_event_loop()
            
            def video_callback(data):
                """视频数据回调 - 从后台线程异步发送到 WebSocket"""
                try:
                    # 使用 run_coroutine_threadsafe 在主事件循环中调度协程
                    asyncio.run_coroutine_threadsafe(
                        self.send(bytes_data=data),
                        loop
                    )
                except Exception as e:
                    logger.error(f"发送视频帧失败: {e}")
            
            # 在线程池中启动 scrcpy（因为它是阻塞的）
            from concurrent.futures import ThreadPoolExecutor
            executor = ThreadPoolExecutor(max_workers=1)
            
            result = await loop.run_in_executor(
                executor,
                lambda: scrcpy_service.start_session(self.device_id, video_callback)
            )
            
            if not result:
                logger.error(f"启动 scrcpy 会话失败: {self.device_id}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': '启动设备会话失败'
                }))
            else:
                logger.info(f"Scrcpy 会话启动成功: {self.device_id}")
                
        except Exception as e:
            logger.error(f"启动 scrcpy 会话异常: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'启动失败: {str(e)}'
            }))
    
    async def send_video_frame(self, data: bytes):
        """发送视频帧到前端"""
        try:
            await self.send(bytes_data=data)
        except Exception as e:
            logger.error(f"发送视频帧异常: {e}")
    
    @database_sync_to_async
    def get_device(self, device_id):
        """获取设备对象"""
        try:
            return AppDevice.objects.get(device_id=device_id)
        except AppDevice.DoesNotExist:
            return None
    
    @database_sync_to_async
    def lock_device(self, device):
        """锁定设备"""
        device.lock(self.user)
        device.status = DeviceStatus.LOCKED
        device.save()
        logger.info(f"设备已锁定: {device.device_id}, user={self.user.username}")
    
    @database_sync_to_async
    def unlock_device(self, device_id):
        """解锁设备"""
        try:
            device = AppDevice.objects.get(device_id=device_id)
            device.unlock()
            device.status = DeviceStatus.AVAILABLE
            device.save()
            logger.info(f"设备已解锁: {device_id}")
        except AppDevice.DoesNotExist:
            logger.warning(f"设备不存在，无法解锁: {device_id}")
