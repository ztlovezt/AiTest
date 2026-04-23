import asyncio
import json
import logging
import re
import subprocess
import threading
import time
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from django.utils import timezone

from .managers.device_manager import DeviceManager
from .models import AppDevice, AppTestConfig, DeviceStatus
from .scrcpy_service import scrcpy_service

logger = logging.getLogger(__name__)


class AppExecutionConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
            self.group_name = f"app_execution_{self.execution_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info("WebSocket connected: execution_id=%s", self.execution_id)
        except Exception as exc:
            logger.error("WebSocket connect failed: %s", exc)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "group_name"):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(
                    "WebSocket disconnected: execution_id=%s, code=%s",
                    self.execution_id,
                    close_code,
                )
        except Exception as exc:
            logger.error("WebSocket disconnect failed: %s", exc)

    async def execution_update(self, event):
        try:
            await self.send_json(event)
        except Exception as exc:
            logger.error("WebSocket push failed: %s", exc)


class RemoteDeviceConsumer(AsyncWebsocketConsumer):
    """基于 AppDevice 主键建立远控 websocket 会话。"""

    LOGCAT_PRIORITY_ORDER = {"V": 0, "D": 1, "I": 2, "W": 3, "E": 4, "F": 5}
    LOGCAT_LINE_PATTERN = re.compile(
        r"^(?P<time>\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d+)\s+"
        r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<priority>[VDIWEF])\s+"
        r"(?P<tag>.*?):\s(?P<message>.*)$"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_pk = None
        self.device_id = None
        self.user = None
        self.session_start_time = None
        self.session_options = {}
        self.adb_path = "adb"

        self.logcat_thread = None
        self.logcat_process = None
        self.logcat_stop_event = threading.Event()
        self.logcat_subscription_lock = threading.Lock()
        self.logcat_subscription = {
            "enabled": False,
            "scope": "device",
            "package_name": "",
            "level": "",
            "keyword": "",
            "lines": 200,
        }
        self.logcat_pid_cache = {"package_name": "", "pid": "", "ts": 0.0}

    async def connect(self):
        try:
            self.device_pk = self.scope["url_route"]["kwargs"]["id"]
            self.user = self.scope["user"]

            if not self.user.is_authenticated:
                logger.warning(
                    "Anonymous user attempted device websocket connect: id=%s",
                    self.device_pk,
                )
                await self.close()
                return

            logger.info(
                "WebSocket connect request: id=%s, user=%s",
                self.device_pk,
                self.user.username,
            )

            device = await self.get_device(self.device_pk)
            if not device:
                logger.error("Device not found: id=%s", self.device_pk)
                await self.close()
                return

            self.device_id = device.device_id
            self.adb_path = await self.get_adb_path()
            # 远控画质参数通过 websocket query 透传，整场会话固定使用这一组配置。
            self.session_options = self._parse_session_options()
            await self.lock_device(device)
            await self.accept()
            self.session_start_time = timezone.now()

            logger.info(
                "WebSocket connected: id=%s, adb_device_id=%s, session_options=%s",
                self.device_pk,
                self.device_id,
                self.session_options,
            )
            await self._send_json(
                {
                    "type": "connected",
                    "message": "连接成功",
                    "device_id": device.pk,
                    "session_options": self.session_options,
                }
            )

            await self.start_scrcpy_session()
        except Exception as exc:
            logger.error("WebSocket connect failed: %s", exc, exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        try:
            logger.info(
                "WebSocket disconnected: id=%s, adb_device_id=%s, code=%s",
                self.device_pk,
                self.device_id,
                close_code,
            )
            self._stop_logcat_stream()
            if self.device_id:
                scrcpy_service.stop_session(self.device_id)
            if self.device_pk:
                await self.unlock_device(self.device_pk)
        except Exception as exc:
            logger.error("WebSocket disconnect failed: %s", exc)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if bytes_data:
                if self.device_id and scrcpy_service.is_session_active(self.device_id):
                    # scrcpy 控制指令走二进制通道，原样透传给后端控制服务。
                    scrcpy_service.send_control(self.device_id, bytes_data)
                return

            if not text_data:
                return

            data = json.loads(text_data)
            command_type = str(data.get("type", "")).strip()
            if command_type == "logcat_subscribe":
                await self._handle_logcat_subscribe(data)
                return
            if command_type == "logcat_unsubscribe":
                await self._handle_logcat_unsubscribe()
                return

            logger.info("Received websocket text command: %s", data)
        except Exception as exc:
            logger.error("Receive failed: %s", exc)

    async def start_scrcpy_session(self):
        try:
            loop = asyncio.get_running_loop()

            def video_callback(data):
                try:
                    # scrcpy 视频流回调在后台线程执行，这里切回主事件循环发送给前端。
                    loop.call_soon_threadsafe(
                        lambda: asyncio.create_task(self.send(bytes_data=data))
                    )
                except Exception as exc:
                    logger.error("Send video frame failed: %s", exc)

            result = await loop.run_in_executor(
                None,
                lambda: scrcpy_service.start_session(
                    self.device_id,
                    video_callback,
                    options=self.session_options,
                ),
            )

            if not result:
                logger.error(
                    "Start scrcpy session failed: adb_device_id=%s",
                    self.device_id,
                )
                await self._send_json(
                    {
                        "type": "error",
                        "message": "启动设备会话失败",
                    }
                )
            else:
                logger.info("Scrcpy session started: adb_device_id=%s", self.device_id)
        except Exception as exc:
            logger.error("Start scrcpy session exception: %s", exc, exc_info=True)
            await self._send_json(
                {
                    "type": "error",
                    "message": f"启动失败: {exc}",
                }
            )

    async def _handle_logcat_subscribe(self, payload):
        subscription = {
            "enabled": self._as_bool(payload.get("enabled"), True),
            "scope": "app" if str(payload.get("scope", "device")).strip() == "app" else "device",
            "package_name": str(payload.get("package_name", "")).strip(),
            "level": str(payload.get("level", "")).strip().upper(),
            "keyword": str(payload.get("keyword", "")).strip(),
            "lines": self._clamp_int(payload.get("lines", 200), 200, 50, 1000),
        }

        with self.logcat_subscription_lock:
            self.logcat_subscription = subscription

        if not subscription["enabled"]:
            self._stop_logcat_stream()
            await self._send_logcat_status("idle", "日志流已关闭")
            return

        self._ensure_logcat_stream()
        await self._send_logcat_status("streaming", "日志流订阅已更新")

    async def _handle_logcat_unsubscribe(self):
        with self.logcat_subscription_lock:
            self.logcat_subscription["enabled"] = False
        self._stop_logcat_stream()
        await self._send_logcat_status("idle", "日志流已关闭")

    def _ensure_logcat_stream(self):
        if self.logcat_thread and self.logcat_thread.is_alive():
            return

        self.logcat_stop_event.clear()
        self.logcat_thread = threading.Thread(
            target=self._logcat_worker,
            args=(asyncio.get_running_loop(),),
            name=f"logcat-stream-{self.device_id}",
            daemon=True,
        )
        self.logcat_thread.start()

    def _stop_logcat_stream(self):
        self.logcat_stop_event.set()

        process = self.logcat_process
        if process and process.poll() is None:
            try:
                process.terminate()
            except Exception:
                logger.debug("Terminate logcat process failed", exc_info=True)

        self.logcat_process = None
        self.logcat_pid_cache = {"package_name": "", "pid": "", "ts": 0.0}

    def _logcat_worker(self, loop):
        manager = DeviceManager(adb_path=self.adb_path)
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "encoding": "utf-8",
            "errors": "replace",
        }
        popen_kwargs.update(manager.subprocess_kwargs)

        process = None
        try:
            command = [
                manager.adb_path,
                "-s",
                self.device_id,
                "logcat",
                "-v",
                "threadtime",
                "-T",
                "1",
            ]
            process = subprocess.Popen(command, **popen_kwargs)
            self.logcat_process = process
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self._send_logcat_status("streaming", "日志流已连接")
                )
            )

            while not self.logcat_stop_event.is_set():
                line = process.stdout.readline() if process.stdout else ""
                if not line:
                    if process.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue

                item = self._parse_logcat_line(line.rstrip())
                if not item or not self._match_logcat_item(manager, item):
                    continue

                loop.call_soon_threadsafe(
                    lambda payload=item: asyncio.create_task(
                        self._send_json(
                            {
                                "type": "logcat_entry",
                                "data": payload,
                            }
                        )
                    )
                )
        except Exception as exc:
            logger.error("Logcat stream failed: %s", exc, exc_info=True)
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self._send_logcat_status("error", f"日志流异常: {exc}")
                )
            )
        finally:
            self.logcat_process = None
            if process and process.poll() is None:
                try:
                    process.kill()
                except Exception:
                    logger.debug("Kill logcat process failed", exc_info=True)

    def _parse_logcat_line(self, line):
        match = self.LOGCAT_LINE_PATTERN.match(line)
        if not match:
            return None
        item = match.groupdict()
        item["raw"] = line
        return item

    def _match_logcat_item(self, manager, item):
        with self.logcat_subscription_lock:
            subscription = dict(self.logcat_subscription)

        if not subscription.get("enabled"):
            return False

        min_level = self.LOGCAT_PRIORITY_ORDER.get(subscription.get("level", ""), 0)
        if self.LOGCAT_PRIORITY_ORDER.get(item.get("priority", "V"), 0) < min_level:
            return False

        keyword = subscription.get("keyword", "").lower()
        if keyword and keyword not in item.get("raw", "").lower():
            return False

        if subscription.get("scope") != "app":
            return True

        package_name = subscription.get("package_name", "")
        if not package_name:
            return False

        pid = self._resolve_logcat_pid(manager, package_name)
        if pid:
            return item.get("pid") == pid

        fallback_text = f"{item.get('tag', '')} {item.get('message', '')}".lower()
        return package_name.lower() in fallback_text

    def _resolve_logcat_pid(self, manager, package_name):
        now = time.time()
        cached = self.logcat_pid_cache
        if (
            cached.get("package_name") == package_name
            and now - float(cached.get("ts", 0.0)) < 2.0
        ):
            return cached.get("pid", "")

        pid = ""
        try:
            pid = manager.get_app_pid(self.device_id, package_name)
        except Exception:
            logger.debug("Resolve app pid failed", exc_info=True)

        self.logcat_pid_cache = {
            "package_name": package_name,
            "pid": pid,
            "ts": now,
        }
        return pid

    async def _send_logcat_status(self, state, message):
        with self.logcat_subscription_lock:
            subscription = dict(self.logcat_subscription)

        await self._send_json(
            {
                "type": "logcat_status",
                "data": {
                    "state": state,
                    "message": message,
                    "connected": bool(self.logcat_process and self.logcat_process.poll() is None),
                    **subscription,
                },
            }
        )

    async def _send_json(self, payload):
        try:
            await self.send(text_data=json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            logger.error("Send websocket json failed: %s", exc)

    def _parse_session_options(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)

        def read_int(name, default, min_value, max_value):
            raw_value = query_params.get(name, [default])[0]
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                return default
            return max(min_value, min(max_value, value))

        return {
            "max_size": read_int("max_size", 900, 480, 1440),
            "max_fps": read_int("max_fps", 45, 15, 60),
            "video_bit_rate": read_int("video_bit_rate", 3072000, 1000000, 12000000),
        }

    def _as_bool(self, value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "off", "no"}

    def _clamp_int(self, value, default, min_value, max_value):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(min_value, min(max_value, parsed))

    @database_sync_to_async
    def get_device(self, device_pk):
        try:
            return AppDevice.objects.get(pk=int(device_pk))
        except (AppDevice.DoesNotExist, TypeError, ValueError):
            return None

    @database_sync_to_async
    def get_adb_path(self):
        config = AppTestConfig.objects.first()
        adb_path = (config.adb_path if config else "") or "adb"
        return str(adb_path).strip() or "adb"

    @database_sync_to_async
    def lock_device(self, device):
        # 远控会话建立后立即锁定设备，避免同一设备被多人同时占用。
        device.lock(self.user)
        device.status = DeviceStatus.LOCKED
        device.save()
        logger.info(
            "Device locked: id=%s, adb_device_id=%s, user=%s",
            device.pk,
            device.device_id,
            self.user.username,
        )

    @database_sync_to_async
    def unlock_device(self, device_pk):
        try:
            device = AppDevice.objects.get(pk=int(device_pk))
            # websocket 断开后恢复设备为可用状态，便于列表页持续展示并支持后续会话。
            device.unlock()
            device.status = DeviceStatus.AVAILABLE
            device.save()
            logger.info(
                "Device unlocked: id=%s, adb_device_id=%s",
                device.pk,
                device.device_id,
            )
        except (AppDevice.DoesNotExist, TypeError, ValueError):
            logger.warning("Device not found while unlocking: id=%s", device_pk)
