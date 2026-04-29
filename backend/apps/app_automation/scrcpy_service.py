# -*- coding: utf-8 -*-
"""APP 远程工作台的轻量级 scrcpy 会话管理器。"""
import logging
import socket
import subprocess
import time
from pathlib import Path
from threading import Thread

logger = logging.getLogger(__name__)

ADB_PATH = "adb"
SCRCPY_SERVER_PATH = str(Path(__file__).parent / "scrcpy-server")
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"
LOCAL_PORT_BASE = 27000
DEFAULT_SESSION_OPTIONS = {
    # 这里的默认值用于“均衡”体验：兼顾清晰度、流畅度和局域网延迟。
    "video_bit_rate": 3072000,
    "max_size": 900,
    "max_fps": 45,
}


class ScrcpyDeviceSession:
    """单设备 scrcpy 会话。"""

    def __init__(self, device_id: str, options=None):
        self.device_id = device_id
        self.video_socket = None
        self.control_socket = None
        self.local_port = None
        self.android_thread = None
        self.video_thread = None
        self.control_thread = None
        self.android_process = None
        self.stop = False
        self.video_callback = None

        session_options = self._sanitize_options(options)
        self.video_bit_rate = str(session_options["video_bit_rate"])
        self.max_size = str(session_options["max_size"])
        self.max_fps = str(session_options["max_fps"])

    def _sanitize_options(self, options):
        # 前端可通过 websocket 查询参数覆盖默认值，这里统一做边界保护，
        # 避免异常参数把 scrcpy 服务直接拉挂。
        merged = dict(DEFAULT_SESSION_OPTIONS)
        if isinstance(options, dict):
            merged.update({key: value for key, value in options.items() if value is not None})

        def clamp(name, default, min_value, max_value):
            try:
                value = int(merged.get(name, default))
            except (TypeError, ValueError):
                value = default
            return max(min_value, min(max_value, value))

        return {
            "video_bit_rate": clamp("video_bit_rate", 3072000, 1000000, 12000000),
            "max_size": clamp("max_size", 900, 480, 1440),
            "max_fps": clamp("max_fps", 45, 15, 60),
        }

    def push_server_to_device(self) -> bool:
        logger.info("[%s] pushing scrcpy-server to device", self.device_id)
        try:
            result = subprocess.run(
                [ADB_PATH, "-s", self.device_id, "push", SCRCPY_SERVER_PATH, DEVICE_SERVER_PATH],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("[%s] push server failed: %s", self.device_id, result.stderr)
                return False
            return True
        except Exception as exc:
            logger.error("[%s] push server exception: %s", self.device_id, exc)
            return False

    def setup_adb_forward(self) -> bool:
        # 为每个设备生成稳定的本地转发端口，避免多设备并发时互相抢占。
        self.local_port = LOCAL_PORT_BASE + hash(self.device_id) % 1000
        logger.info("[%s] setting adb forward on port %s", self.device_id, self.local_port)
        try:
            subprocess.run(
                [ADB_PATH, "-s", self.device_id, "forward", "--remove", f"tcp:{self.local_port}"],
                capture_output=True,
                timeout=5,
            )
            result = subprocess.run(
                [ADB_PATH, "-s", self.device_id, "forward", f"tcp:{self.local_port}", "localabstract:scrcpy"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                logger.error("[%s] adb forward failed: %s", self.device_id, result.stderr)
                return False
            return True
        except Exception as exc:
            logger.error("[%s] adb forward exception: %s", self.device_id, exc)
            return False

    def start_server(self):
        # scrcpy server 运行在设备侧，视频流和控制流都通过这里的参数控制质量。
        logger.info(
            "[%s] starting scrcpy server with bitrate=%s max_size=%s max_fps=%s",
            self.device_id,
            self.video_bit_rate,
            self.max_size,
            self.max_fps,
        )
        try:
            server_cmd = [
                ADB_PATH,
                "-s",
                self.device_id,
                "shell",
                (
                    f"CLASSPATH={DEVICE_SERVER_PATH} app_process / com.genymobile.scrcpy.Server 3.1 "
                    "tunnel_forward=true control=true video=true audio=false log_level=info "
                    f"video_bit_rate={self.video_bit_rate} "
                    f"max_size={self.max_size} "
                    f"max_fps={self.max_fps} "
                    "lock_video_orientation=-1"
                ),
            ]
            self.android_process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            time.sleep(2)
            if self.android_process.poll() is not None:
                stdout, stderr = self.android_process.communicate(timeout=2)
                logger.error(
                    "[%s] scrcpy server exited early: stdout=%s stderr=%s",
                    self.device_id,
                    stdout,
                    stderr,
                )
                return

            self._read_server_output()
            self.android_process.wait()
            logger.info("[%s] scrcpy server stopped", self.device_id)
        except Exception as exc:
            logger.error(
                "[%s] scrcpy server exception: %s", self.device_id, exc, exc_info=True
            )

    def _read_server_output(self):
        if not self.android_process or not self.android_process.stderr:
            return

        def reader():
            # 单独起线程消费 stderr，避免子进程输出阻塞导致会话卡死。
            while not self.stop:
                line = self.android_process.stderr.readline()
                if not line:
                    break
                logger.debug(
                    "[%s] scrcpy: %s",
                    self.device_id,
                    line.decode(errors="ignore").strip(),
                )

        Thread(target=reader, daemon=True, name=f"scrcpy-log-{self.device_id}").start()

    def receive_video_data(self):
        if not self.video_socket:
            return
        try:
            # scrcpy 首字节是虚拟设备元数据，这里先消费掉，后续再持续转发裸视频流。
            self.video_socket.recv(1)
            while not self.stop and self.video_socket:
                data = self.video_socket.recv(8192)
                if not data:
                    break
                if self.video_callback:
                    self.video_callback(data)
        except Exception as exc:
            if not self.stop:
                logger.error(
                    "[%s] video recv exception: %s", self.device_id, exc, exc_info=True
                )

    def handle_control_conn(self):
        if not self.control_socket:
            return
        try:
            # 控制通道同样会先下发一个握手字节，先读掉再进入保活循环。
            self.control_socket.recv(1)
            while not self.stop and self.control_socket:
                try:
                    self.control_socket.settimeout(0.5)
                    data = self.control_socket.recv(64)
                    if not data:
                        break
                except socket.timeout:
                    continue
        except Exception as exc:
            if not self.stop:
                logger.error("[%s] control recv exception: %s", self.device_id, exc)

    def start(self, video_callback) -> bool:
        self.video_callback = video_callback
        self.stop = False

        try:
            # 先确认 ADB 设备在线，避免后续 push / forward / socket 连接都失败。
            check_result = subprocess.run(
                [ADB_PATH, "-s", self.device_id, "get-state"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_result.returncode != 0 or "device" not in (check_result.stdout or "").strip():
                logger.error(
                    "[%s] device is not ready: %s",
                    self.device_id,
                    check_result.stdout or check_result.stderr,
                )
                return False
        except Exception as exc:
            logger.error("[%s] device check exception: %s", self.device_id, exc)
            return False

        if not self.push_server_to_device():
            return False
        if not self.setup_adb_forward():
            return False

        self.android_thread = Thread(
            target=self.start_server,
            daemon=True,
            name=f"scrcpy-android-{self.device_id}",
        )
        self.android_thread.start()
        # 给设备侧 server 一个短暂启动窗口，避免本地 socket 抢跑连接失败。
        time.sleep(1)

        try:
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.video_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.video_socket.settimeout(5)
            self.video_socket.connect(("localhost", self.local_port))
            self.video_socket.settimeout(None)
        except Exception as exc:
            logger.error("[%s] video socket connect failed: %s", self.device_id, exc)
            self.stop_all()
            return False

        try:
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.control_socket.settimeout(5)
            self.control_socket.connect(("localhost", self.local_port))
            self.control_socket.settimeout(None)
        except Exception as exc:
            logger.error("[%s] control socket connect failed: %s", self.device_id, exc)
            self.stop_all()
            return False

        self.video_thread = Thread(
            target=self.receive_video_data,
            daemon=True,
            name=f"scrcpy-video-{self.device_id}",
        )
        self.control_thread = Thread(
            target=self.handle_control_conn,
            daemon=True,
            name=f"scrcpy-control-{self.device_id}",
        )
        self.video_thread.start()
        self.control_thread.start()
        logger.info("[%s] scrcpy session started", self.device_id)
        return True

    def stop_all(self):
        logger.info("[%s] stopping scrcpy session", self.device_id)
        self.stop = True

        # 先关 socket，再回收线程和子进程，避免线程一直阻塞在 recv。
        for sock in (self.video_socket, self.control_socket):
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        for thread in (self.video_thread, self.control_thread, self.android_thread):
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=2)
                except Exception:
                    pass

        if self.android_process:
            try:
                self.android_process.terminate()
                self.android_process.wait(timeout=2)
            except Exception:
                pass

        if self.local_port:
            try:
                subprocess.run(
                    [ADB_PATH, "-s", self.device_id, "forward", "--remove", f"tcp:{self.local_port}"],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

        self.video_socket = None
        self.control_socket = None
        self.video_thread = None
        self.control_thread = None
        self.android_thread = None
        self.android_process = None
        self.local_port = None

    def send_control(self, data: bytes):
        if not self.control_socket:
            return
        try:
            # 控制事件已经在 websocket 消费端做了高频丢弃，这里直接下发到 scrcpy。
            self.control_socket.sendall(data)
        except Exception as exc:
            logger.error("[%s] send control failed: %s", self.device_id, exc)


class ScrcpyService:
    """按 adb 设备标识管理 scrcpy 会话。"""

    def __init__(self):
        self.sessions = {}

    def start_session(self, device_id: str, video_callback, options=None) -> bool:
        if device_id in self.sessions:
            # 同设备重复连接时先清掉旧会话，避免 forward 端口和 socket 残留。
            self.stop_session(device_id)

        session = ScrcpyDeviceSession(device_id, options=options)
        if session.start(video_callback):
            self.sessions[device_id] = session
            return True
        return False

    def stop_session(self, device_id: str):
        session = self.sessions.pop(device_id, None)
        if session:
            session.stop_all()
            logger.info("scrcpy session stopped for %s", device_id)

    def send_control(self, device_id: str, data: bytes):
        session = self.sessions.get(device_id)
        if session:
            session.send_control(data)

    def is_session_active(self, device_id: str) -> bool:
        return device_id in self.sessions

    def cleanup_all(self):
        for device_id in list(self.sessions.keys()):
            self.stop_session(device_id)


scrcpy_service = ScrcpyService()
