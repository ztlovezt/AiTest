# -*- coding: utf-8 -*-
"""
Scrcpy Service - 基于 web-scrcpy 的远程设备控制服务
提供设备管理、ADB转发、视频流和控制命令功能
"""
import logging
import subprocess
import socket
import time
import os
from threading import Thread
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置常量
ADB_PATH = "adb"
SCRCPY_SERVER_PATH = str(Path(__file__).parent / "scrcpy-server")
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"
LOCAL_PORT_BASE = 27000  # 基础端口，每个设备使用不同端口


class ScrcpyDeviceSession:
    """单个设备的 Scrcpy 会话"""
    
    def __init__(self, device_id: str):
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
        # 默认配置：1Mbps 码率（参考原始 web-scrcpy）
        self.video_bit_rate = "1024000"  # 1Mbps
        self.max_size = "720"            # 720p（低延迟优先）
        self.max_fps = "60"              # 30fps（流畅且延迟低）
        
        # 检测设备类型并优化参数
        self._optimize_for_device_type()
    
    def _optimize_for_device_type(self):
        """根据设备类型优化 max_size 和 max_fps，码率统一使用 1Mbps"""
        try:
            # 检查是否为模拟器
            result = subprocess.run(
                [ADB_PATH, "-s", self.device_id, "shell", "getprop", "ro.product.model"],
                capture_output=True, text=True, timeout=5
            )
            model = result.stdout.strip().lower()
            
            # 常见模拟器标识
            emulator_keywords = ['emulator', 'sdk', 'android sdk', 'genymotion']
            is_emulator = any(keyword in model for keyword in emulator_keywords) or self.device_id.startswith('emulator-')
            
            if is_emulator:
                # 模拟器性能强，可以使用更高配置
                self.max_size = "1080"  # 1080p（高画质）
                self.max_fps = "60"     # 60fps（更流畅）
                logger.info(f"[{self.device_id}] Detected emulator, using high quality: 1080p@60fps")
            else:
                # 真机 USB 连接，优先低延迟
                self.max_size = "720"   # 720p（平衡画质和延迟）
                self.max_fps = "30"     # 30fps（足够流畅）
                logger.info(f"[{self.device_id}] Detected real device, using low latency: 720p@30fps")
        except Exception as e:
            logger.warning(f"[{self.device_id}] Failed to detect device type: {e}, using default: 720p@30fps")
    
    def push_server_to_device(self) -> bool:
        """推送 scrcpy-server 到设备"""
        logger.info(f"[{self.device_id}] Pushing scrcpy-server to device...")
        try:
            cmd = [ADB_PATH, "-s", self.device_id, "push", SCRCPY_SERVER_PATH, DEVICE_SERVER_PATH]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"[{self.device_id}] Error pushing server: {result.stderr}")
                return False
            logger.info(f"[{self.device_id}] Server pushed successfully")
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] Failed to push server: {e}")
            return False
    
    def setup_adb_forward(self) -> bool:
        """设置 ADB 端口转发"""
        # 为每个设备分配唯一端口
        self.local_port = LOCAL_PORT_BASE + hash(self.device_id) % 1000
        
        logger.info(f"[{self.device_id}] Setting up ADB forward: tcp:{self.local_port} -> localabstract:scrcpy")
        try:
            # 先移除可能存在的转发
            subprocess.run([ADB_PATH, "-s", self.device_id, "forward", "--remove", f"tcp:{self.local_port}"], 
                          capture_output=True, timeout=5)
            
            # 设置新的转发
            cmd = [ADB_PATH, "-s", self.device_id, "forward", f"tcp:{self.local_port}", "localabstract:scrcpy"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error(f"[{self.device_id}] Error setting up forward: {result.stderr}")
                return False
            logger.info(f"[{self.device_id}] ADB forward set up on port {self.local_port}")
            return True
        except Exception as e:
            logger.error(f"[{self.device_id}] Failed to setup ADB forward: {e}")
            return False
    
    def start_server(self):
        """启动 scrcpy server - 参考原始 web-scrcpy 实现"""
        logger.info(f"[{self.device_id}] Starting scrcpy server...")
        try:
            # 使用与原始 web-scrcpy 相同的简化命令
            # 但需要显式启用 video 和 control，否则可能不发送数据
            server_cmd = [
                ADB_PATH, "-s", self.device_id, "shell",
                f"CLASSPATH={DEVICE_SERVER_PATH} app_process / com.genymobile.scrcpy.Server 3.1 "
                f"tunnel_forward=true control=true video=true audio=false log_level=info "
                f"video_bit_rate={self.video_bit_rate}"
            ]
            logger.info(f"[{self.device_id}] Server command: {' '.join(server_cmd)}")
            
            # 使用 PIPE 以便捕获输出进行诊断
            self.android_process = subprocess.Popen(
                server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info(f"[{self.device_id}] Server process started, PID: {self.android_process.pid}")
            
            # 等待服务器启动完成
            time.sleep(3)
            
            # 检查进程是否还在运行
            if self.android_process.poll() is not None:
                returncode = self.android_process.returncode
                logger.error(f"[{self.device_id}] Server process exited with code {returncode}")
                # 读取错误输出
                try:
                    stdout, stderr = self.android_process.communicate(timeout=2)
                    if stdout:
                        logger.error(f"[{self.device_id}] Server stdout: {stdout.decode(errors='ignore')[:500]}")
                    if stderr:
                        logger.error(f"[{self.device_id}] Server stderr: {stderr.decode(errors='ignore')[:500]}")
                except:
                    pass
                return
            
            logger.info(f"[{self.device_id}] Server is running")
            
            # 后台线程读取输出（避免阻塞）
            def read_output():
                while not self.stop:
                    line = self.android_process.stderr.readline()
                    if not line:
                        break
                    logger.debug(f"[{self.device_id}] Server: {line.decode(errors='ignore').strip()}")
            
            import threading
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # 等待进程结束
            self.android_process.wait()
            logger.info(f"[{self.device_id}] Server stopped")
        except Exception as e:
            logger.error(f"[{self.device_id}] Server error: {e}", exc_info=True)
    
    def receive_video_data(self):
        """接收视频数据线程 - 参考原始 web-scrcpy 实现"""
        try:
            if not self.video_socket:
                logger.error(f"[{self.device_id}] Video socket is None")
                return
            
            logger.info(f"[{self.device_id}] Starting to receive video data...")
            # 读取初始字节
            initial_byte = self.video_socket.recv(1)
            logger.info(f"[{self.device_id}] Received initial byte: {len(initial_byte)} bytes")
            
            count = 0
            while not self.stop:
                if not self.video_socket:
                    break
                try:
                    data = self.video_socket.recv(20480)
                    if not data:
                        logger.warning(f"[{self.device_id}] Video socket returned empty data")
                        break
                except Exception as e:
                    logger.error(f"[{self.device_id}] Video recv error: {e}")
                    break
                
                count += 1
                if count <= 10 or count % 100 == 0:
                    logger.info(f"[{self.device_id}] Received video chunk #{count}: {len(data)} bytes")
                
                # 直接回调
                if self.video_callback:
                    try:
                        self.video_callback(data)
                    except Exception as e:
                        logger.error(f"[{self.device_id}] Video callback error: {e}")
                else:
                    logger.warning(f"[{self.device_id}] Video callback is None!")
                    
            logger.info(f"[{self.device_id}] Video reception stopped after {count} chunks")
        except Exception as e:
            if not self.stop:
                logger.error(f"[{self.device_id}] Video thread error: {e}", exc_info=True)
    
    def handle_control_conn(self):
        """处理控制连接 - 参考原始 web-scrcpy 实现，保持连接活跃"""
        logger.info(f"[{self.device_id}] Control connection established")
        try:
            if not self.control_socket:
                return
            
            # 读取初始确认字节
            self.control_socket.recv(1)
            
            # 保持连接活跃，等待发送命令
            while not self.stop:
                if not self.control_socket:
                    break
                try:
                    # 使用较小的超时以便快速响应stop信号
                    self.control_socket.settimeout(0.5)
                    data = self.control_socket.recv(64)
                    if not data:
                        break
                except socket.timeout:
                    # 超时是正常的，继续循环检查stop标志
                    continue
                except Exception as e:
                    logger.error(f"[{self.device_id}] Control recv error: {e}")
                    break
            
            logger.info(f"[{self.device_id}] Control connection stopped")
        except Exception as e:
            if not self.stop:
                logger.error(f"[{self.device_id}] Control thread error: {e}")
    
    def start(self, video_callback) -> bool:
        """启动完整的 scrcpy 会话"""
        self.video_callback = video_callback
        self.stop = False
        
        # 检查设备是否在线
        try:
            result = subprocess.run(
                [ADB_PATH, "-s", self.device_id, "devices"],
                capture_output=True, text=True, timeout=5
            )
            if "device" not in result.stdout:
                logger.error(f"[{self.device_id}] Device not found or offline")
                return False
        except Exception as e:
            logger.error(f"[{self.device_id}] Device check failed: {e}")
            return False
        
        # 推送服务器
        if not self.push_server_to_device():
            return False
        
        # 设置端口转发
        if not self.setup_adb_forward():
            return False
        
        # 启动服务器线程
        time.sleep(0.5)
        logger.info(f"[{self.device_id}] Starting scrcpy server thread...")
        self.android_thread = Thread(target=self.start_server, daemon=True, name=f"scrcpy-android-{self.device_id}")
        self.android_thread.start()
        
        # 等待服务器启动（参考原始实现，1秒足够）
        logger.info(f"[{self.device_id}] Waiting for server to start...")
        time.sleep(1)
        
        # 连接视频socket
        try:
            logger.info(f"[{self.device_id}] Connecting to video socket on port {self.local_port}...")
            self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.video_socket.settimeout(5)
            self.video_socket.connect(('localhost', self.local_port))
            self.video_socket.settimeout(None)
            logger.info(f"[{self.device_id}] Video connection established")
        except Exception as e:
            logger.error(f"[{self.device_id}] Video connection failed: {e}")
            self.stop_all()
            return False
        
        # 连接控制socket
        try:
            logger.info(f"[{self.device_id}] Connecting to control socket on port {self.local_port}...")
            self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.control_socket.settimeout(5)
            self.control_socket.connect(('localhost', self.local_port))
            self.control_socket.settimeout(None)
            logger.info(f"[{self.device_id}] Control connection established")
        except Exception as e:
            logger.error(f"[{self.device_id}] Control connection failed: {e}")
            self.stop_all()
            return False
        
        # 启动接收线程
        self.video_thread = Thread(target=self.receive_video_data, daemon=True, name=f"scrcpy-video-{self.device_id}")
        self.control_thread = Thread(target=self.handle_control_conn, daemon=True, name=f"scrcpy-control-{self.device_id}")
        
        self.video_thread.start()
        self.control_thread.start()
        
        logger.info(f"[{self.device_id}] Scrcpy session started successfully")
        return True
    
    def stop_all(self):
        """停止所有线程和连接"""
        logger.info(f"[{self.device_id}] Stopping Scrcpy session...")
        self.stop = True
        
        # 关闭sockets以中断阻塞的recv
        for sock in [self.video_socket, self.control_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        
        # 等待线程结束
        for thread in [self.video_thread, self.control_thread, self.android_thread]:
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=2)
                except:
                    pass
        
        # 终止android进程
        if self.android_process:
            try:
                self.android_process.terminate()
                self.android_process.wait(timeout=2)
            except:
                pass
        
        # 清理ADB转发
        if self.local_port:
            try:
                subprocess.run(
                    [ADB_PATH, "-s", self.device_id, "forward", "--remove", f"tcp:{self.local_port}"],
                    capture_output=True, timeout=5
                )
            except:
                pass
        
        # 重置所有引用
        self.video_socket = None
        self.control_socket = None
        self.video_thread = None
        self.control_thread = None
        self.android_thread = None
        self.android_process = None
        self.local_port = None
        
        logger.info(f"[{self.device_id}] Scrcpy session stopped")
    
    def send_control(self, data: bytes):
        """发送控制命令 - 使用非阻塞方式"""
        if self.control_socket:
            try:
                self.control_socket.sendall(data)  # 使用sendall确保完整发送
            except Exception as e:
                logger.error(f"[{self.device_id}] Failed to send control: {e}")


class ScrcpyService:
    """Scrcpy 服务管理器 - 管理多个设备会话"""
    
    def __init__(self):
        self.sessions = {}  # device_id -> ScrcpyDeviceSession
    
    def start_session(self, device_id: str, video_callback) -> bool:
        """启动设备会话"""
        if device_id in self.sessions:
            logger.warning(f"Session already exists for {device_id}, stopping first...")
            self.stop_session(device_id)
        
        session = ScrcpyDeviceSession(device_id)
        if session.start(video_callback):
            self.sessions[device_id] = session
            return True
        return False
    
    def stop_session(self, device_id: str):
        """停止设备会话"""
        if device_id in self.sessions:
            self.sessions[device_id].stop_all()
            del self.sessions[device_id]
            logger.info(f"Session stopped for {device_id}")
    
    def send_control(self, device_id: str, data: bytes):
        """发送控制命令到指定设备"""
        if device_id in self.sessions:
            self.sessions[device_id].send_control(data)
    
    def is_session_active(self, device_id: str) -> bool:
        """检查会话是否活跃"""
        return device_id in self.sessions
    
    def cleanup_all(self):
        """清理所有会话"""
        for device_id in list(self.sessions.keys()):
            self.stop_session(device_id)


# 全局服务实例
scrcpy_service = ScrcpyService()
