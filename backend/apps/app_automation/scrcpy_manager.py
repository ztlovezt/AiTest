# -*- coding: utf-8 -*-
import subprocess
import socket
import time
import logging
import threading
import os
import struct
from django.conf import settings

logger = logging.getLogger(__name__)

class ScrcpyManager:
    """
    Scrcpy 控制管理器
    使用 scrcpy-server 提供的二进制协议进行高速控制
    """
    def __init__(self, device_id, adb_path='adb', jar_path=None):
        self.device_id = device_id
        self.adb_path = adb_path
        # 默认使用与当前文件同目录下的 scrcpy-server
        self.jar_path = jar_path or os.path.join(os.path.dirname(__file__), 'scrcpy-server')
        self.device_server_path = '/data/local/tmp/scrcpy-server.jar'
        self.local_port = None
        self.video_socket = None
        self.control_socket = None
        self.device_name_header = None
        self.codec_info_header = None
        self.server_process = None
        self.is_running = False
        self._stop_event = threading.Event()

    def _find_free_port(self):
        """查找本地空闲端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def start(self):
        """启动 scrcpy 服务 (推送 JAR, 端口转发, 运行 server 进程)"""
        if self.is_running and self.server_process and self.server_process.poll() is None:
            return True
            
        try:
            # 1. 推送 server jar
            logger.info(f"正在推送 scrcpy-server 到设备 {self.device_id}...")
            subprocess.run([self.adb_path, '-s', self.device_id, 'push', self.jar_path, self.device_server_path], check=True, capture_output=True)

            # 2. 端口转发
            if not self.local_port:
                self.local_port = self._find_free_port()
            logger.info(f"设置端口转发: tcp:{self.local_port} -> localabstract:scrcpy")
            subprocess.run([self.adb_path, '-s', self.device_id, 'forward', f'tcp:{self.local_port}', 'localabstract:scrcpy'], check=True, capture_output=True)

            # 3. 启动设备端服务 (提高码率和帧率限制，限制分辨率以提升性能)
            server_cmd = [
                self.adb_path, '-s', self.device_id, 'shell',
                f'CLASSPATH={self.device_server_path} app_process / com.genymobile.scrcpy.Server 3.1 '
                f'tunnel_forward=true control=true video=true audio=false log_level=info '
                f'video_bit_rate=4000000 max_size=1080 max_fps=60'
            ]
            logger.info(f"启动设备端 scrcpy-server: {' '.join(server_cmd)}")
            self.server_process = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.is_running = True
            return True
        except Exception as e:
            logger.error(f"启动 ScrcpyManager 失败: {e}")
            self.is_running = False
            return False

    def connect(self):
        """连接 Socket (视频和控制)"""
        if not self.is_running or not self.server_process or self.server_process.poll() is not None:
            logger.info("Scrcpy server 不在运行或已退出，正在尝试启动...")
            if not self.start():
                return False

        try:
            # 清理旧连接
            self.stop_sockets()

            # 等待服务器就绪，增加重试机制
            logger.info(f"尝试连接到视频 Socket (localhost:{self.local_port})...")
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.video_socket.settimeout(2.0) # 设置连接和初次读取的超时
            
            connected = False
            for i in range(10):
                try:
                    time.sleep(0.5) # 给 adb forward 和 server 一点时间
                    self.video_socket.connect(('localhost', self.local_port))
                    connected = True
                    logger.info(f"视频 Socket 连接成功 (尝试 {i+1}/10)")
                    break
                except (ConnectionRefusedError, socket.timeout) as e:
                    logger.debug(f"视频 Socket 连接失败 ({type(e).__name__})，重试 {i+1}/10...")
                    continue
            
            if not connected:
                # 增加失败时的诊断信息
                if self.server_process and self.server_process.poll() is not None:
                    # 仅当进程已退出时读取输出，避免阻塞
                    stdout, stderr = self.server_process.communicate()
                    logger.error(f"scrcpy-server 已退出。stdout: {stdout.decode(errors='ignore')}")
                    logger.error(f"scrcpy-server 已退出。stderr: {stderr.decode(errors='ignore')}")
                raise Exception("无法连接到视频 Socket，scrcpy-server 可能启动失败或无响应")
            
            logger.info(f"尝试连接到控制 Socket (localhost:{self.local_port})...")
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(5.0)
            self.control_socket.connect(('localhost', self.local_port))
            
            # 读取初始字节和协议头
            try:
                dummy_video = self.video_socket.recv(1)
                logger.info(f"视频连接已建立，接收到初始字节: {dummy_video.hex()}")
                
                self.device_name_header = self.video_socket.recv(64)
                logger.info(f"设备名称: {self.device_name_header.decode('utf-8', errors='ignore').strip(chr(0))}")
                
                self.codec_info_header = self.video_socket.recv(12)
                if len(self.codec_info_header) == 12:
                    _, w, h = struct.unpack('>III', self.codec_info_header)
                    self.video_width = w
                    self.video_height = h
                    logger.info(f"解析视频编码信息：width={w}, height={h}")
                else:
                    self.video_width = None
                    self.video_height = None
                    logger.info(f"视频编码信息长度异常：{len(self.codec_info_header)}")
                
            except socket.timeout:
                logger.warning("视频 Socket 接收协议头超时，可能导致前端解析失败")

            # 控制 socket 接收 1 字节 dummy
            try:
                self.control_socket.settimeout(0.5)
                dummy_control = self.control_socket.recv(1)
                if dummy_control:
                    logger.info(f"控制连接已建立，接收到初始字节: {dummy_control.hex()}")
            except socket.timeout:
                logger.info("控制 Socket 未发送初始字节 (正常现象)")
            finally:
                self.control_socket.settimeout(5.0)

            return True
        except Exception as e:
            logger.error(f"连接 Scrcpy Sockets 失败: {e}", exc_info=True)
            self.stop_sockets()
            return False

    def stop_sockets(self):
        """仅关闭 Socket 连接，不杀死 server 进程"""
        if self.video_socket:
            try: self.video_socket.close()
            except: pass
            self.video_socket = None
        if self.control_socket:
            try: self.control_socket.close()
            except: pass
            self.control_socket = None

    def stop(self):
        """停止服务并清理进程"""
        self.stop_sockets()
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=2)
            except:
                pass
            self.server_process = None
        self.is_running = False

        if self.local_port:
            try:
                subprocess.run([self.adb_path, '-s', self.device_id, 'forward', '--remove', f'tcp:{self.local_port}'], capture_output=True)
            except:
                pass
            self.local_port = None

    def send_tap(self, x, y, width, height):
        """发送点击事件"""
        if not self.is_running or not self.control_socket:
            return False
        
        try:
            # Touch Event Protocol (Type=2)
            # Action(1), PointerID(8), X(4), Y(4), Width(2), Height(2), Pressure(2), ActionButton(4), Buttons(4)
            
            # Down
            msg_down = self._build_touch_msg(0, x, y, width, height)
            self.control_socket.sendall(msg_down)
            
            # Up
            msg_up = self._build_touch_msg(1, x, y, width, height)
            self.control_socket.sendall(msg_up)
            return True
        except Exception as e:
            logger.error(f"发送点击事件失败: {e}")
            return False

    def send_swipe(self, x1, y1, x2, y2, width, height, duration=300):
        """发送滑动事件"""
        if not self.is_running or not self.control_socket:
            return False
        
        try:
            # Down
            self.control_socket.sendall(self._build_touch_msg(0, x1, y1, width, height))
            
            # Move (可以根据需要发送多个中间点，这里简单发送终点)
            self.control_socket.sendall(self._build_touch_msg(2, x2, y2, width, height))
            
            # Up
            self.control_socket.sendall(self._build_touch_msg(1, x2, y2, width, height))
            return True
        except Exception as e:
            logger.error(f"发送滑动事件失败: {e}")
            return False

    def send_keycode(self, keycode):
        """发送按键事件"""
        if not self.is_running or not self.control_socket:
            return False
        
        try:
            # Key Event Protocol (Type=0)
            # Action(1), Keycode(4), Repeat(4), MetaState(4)
            
            # Down
            msg_down = struct.pack('>BBIII', 0, 0, keycode, 0, 0)
            self.control_socket.sendall(msg_down)
            
            # Up
            msg_up = struct.pack('>BBIII', 0, 1, keycode, 0, 0)
            self.control_socket.sendall(msg_up)
            return True
        except Exception as e:
            logger.error(f"发送按键事件失败: {e}")
            return False

    def send_raw_touch(self, action, x, y, width, height):
        """发送原始触屏事件 (0=Down, 1=Up, 2=Move)"""
        if not self.is_running or not self.control_socket:
            return False
        
        try:
            msg = self._build_touch_msg(action, x, y, width, height)
            self.control_socket.sendall(msg)
            return True
        except Exception as e:
            logger.error(f"发送原始触屏事件失败: {e}")
            return False

    def _build_touch_msg(self, action, x, y, width, height):
        """构建触屏二进制消息"""
        # Type: 2 (Touch)
        # Action: 0=Down, 1=Up, 2=Move
        # PointerID: 8 bytes (0xFFFFFFFFFFFFFFFD for virtual finger, used in web-scrcpy)
        # X: 4 bytes, Y: 4 bytes
        # Width: 2 bytes, Height: 2 bytes
        # Pressure: 2 bytes (0-65535)
        # ActionButton: 4 bytes (0)
        # Buttons: 4 bytes (0)
        
        # 修正后的格式串: > (大端), B(Type), B(Action), Q(PointerID), I(X), I(Y), H(Width), H(Height), H(Pressure), I(ActionButton), I(Buttons)
        # 使用 0xFFFFFFFFFFFFFFFD 作为 PointerID
        return struct.pack('>BBQIIHHHII', 
            2, action, 0xFFFFFFFFFFFFFFFD, 
            int(x), int(y), int(width), int(height), 
            65535 if action != 1 else 0, # Pressure
            0, 0 # ActionButton, Buttons
        )
