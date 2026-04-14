from threading import Thread
import subprocess
import socket
import time
import os
import logging

ADB_PATH = "adb"
SCRCPY_SERVER_PATH = "scrcpy-server"
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"
LOCAL_PORT = 5555
DEVICE_ID = os.getenv('DEVICE_ID', None)  # 从环境变量获取设备 ID

logger = logging.getLogger(__name__)


class Scrcpy:
    def __init__(self):
        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None

        self.android_thread = None
        self.video_thread = None
        self.audio_thread = None
        self.control_thread = None
        self.android_process = None

    def push_server_to_device(self):
        logger.info("Pushing scrcpy-server.jar to device...")
        cmd = [ADB_PATH]
        if DEVICE_ID:
            cmd.extend(["-s", DEVICE_ID])
        cmd.extend(["push", SCRCPY_SERVER_PATH, DEVICE_SERVER_PATH])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error pushing server: {result.stderr}")
            return False
        logger.info("Server pushed successfully")
        return True

    def setup_adb_forward(self):
        logger.info(f"Setting up ADB forward: tcp:{LOCAL_PORT} -> localabstract:scrcpy")
        cmd = [ADB_PATH]
        if DEVICE_ID:
            cmd.extend(["-s", DEVICE_ID])
        cmd.extend(["forward", f"tcp:{LOCAL_PORT}", "localabstract:scrcpy"])
        subprocess.run(cmd, check=True)
        logger.info("ADB forward set up successfully")

    def start_server(self):
        logger.info("Starting scrcpy server in background...")
        cmd = [ADB_PATH]
        if DEVICE_ID:
            cmd.extend(["-s", DEVICE_ID])
        cmd.extend(["shell", f"CLASSPATH={DEVICE_SERVER_PATH} app_process / com.genymobile.scrcpy.Server 3.1 tunnel_forward=true log_level=VERBOSE video_bit_rate=" + self.video_bit_rate])
        self.android_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while not self.stop:
            stderr_line = self.android_process.stderr.readline().decode().strip()
            if not stderr_line:
                break
            if stderr_line:
                logger.warning(f"Server stderr: {stderr_line}")
        self.android_process.wait()
        logger.info("Server stopped")

    def receive_video_data(self):
        logger.info("Receiving video data (H.264)...")
        try:
            if not self.video_socket:
                return
            self.video_socket.recv(1)
            count = 0
            while not self.stop:
                if not self.video_socket:
                    break
                try:
                    data = self.video_socket.recv(20480)
                    if not data:
                        break
                except:
                    break
                count += 1
                if count % 100 == 0:
                    logger.info(f"Received {count} video chunks")
                self.video_callback(data)
            logger.info("Video data reception stopped")
        except Exception as e:
            if not self.stop:
                logger.error(f"Error receiving video data: {e}")

    def receive_audio_data(self):
        logger.info("Receiving audio data...")
        try:
            if not self.audio_socket:
                return
            self.audio_socket.recv(1)
            while not self.stop:
                if not self.audio_socket:
                    break
                try:
                    data = self.audio_socket.recv(1024)
                    if not data:
                        break
                except:
                    break
            logger.info("Audio data reception stopped")
        except Exception as e:
            if not self.stop:
                logger.error(f"Error receiving audio data: {e}")

    def handle_control_conn(self):
        logger.info("Control connection established (idle)...")
        try:
            if not self.control_socket:
                return
            self.control_socket.recv(1)
            while not self.stop:
                if not self.control_socket:
                    break
                try:
                    data = self.control_socket.recv(1024)
                    if not data:
                        break
                    logger.debug(f"Control message: {data}")
                except:
                    break
            logger.info("Control connection stopped")
        except Exception as e:
            if not self.stop:
                logger.error(f"Error in control connection: {e}")

    def scrcpy_start(self, video_callback, video_bit_rate):
        self.video_bit_rate = video_bit_rate
        self.video_callback = video_callback
        self.stop = False

        cmd = [ADB_PATH]
        if DEVICE_ID:
            cmd.extend(["-s", DEVICE_ID])
        cmd.extend(["devices"])
        result = subprocess.run(cmd, capture_output=True, text=True)
        if "device" not in result.stdout:
            logger.error("No device found. Please connect your Android device via USB.")
            return
        logger.info(f"Devices found:\n{result.stdout}")

        if not self.push_server_to_device():
            print("Failed to push server files to device.")
            return

        self.setup_adb_forward()
        self.android_thread = Thread(target=self.start_server, daemon=True)
        self.android_thread.start()
        time.sleep(1)

        # video connection
        logger.info("Connecting to video socket...")
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.video_socket.connect(('localhost', LOCAL_PORT))
        logger.info("Video connection established")

        # audio connection
        logger.info("Connecting to audio socket...")
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.audio_socket.connect(('localhost', LOCAL_PORT))
        logger.info("Audio connection established")

        # contorl connection
        logger.info("Connecting to control socket...")
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.connect(('localhost', LOCAL_PORT))
        logger.info("Control connection established")

        self.video_thread = Thread(target=self.receive_video_data, daemon=True)
        self.audio_thread = Thread(target=self.receive_audio_data, daemon=True)
        self.control_thread = Thread(target=self.handle_control_conn, daemon=True)
        self.video_thread.start()
        self.audio_thread.start()
        self.control_thread.start()
        logger.info("Background tasks started")

    def scrcpy_stop(self):
        logger.info("Stopping Scrcpy")
        self.stop = True

        # 先关闭所有socket，以中断阻塞的recv调用
        for sock in [self.video_socket, self.audio_socket, self.control_socket]:
            if sock:
                try:
                    sock.close()
                except:
                    pass

        # 等待线程结束
        for thread in [self.video_thread, self.audio_thread, self.control_thread, self.android_thread]:
            if thread and thread.is_alive():
                try:
                    thread.join(timeout=1)
                except:
                    pass

        # 停止android进程
        if self.android_process:
            try:
                self.android_process.terminate()
                self.android_process.wait(timeout=2)
            except:
                pass

        # 重置所有socket和线程引用
        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None
        self.video_thread = None
        self.audio_thread = None
        self.control_thread = None
        self.android_thread = None
        self.android_process = None

        logger.info("Scrcpy stopped")

    def scrcpy_send_control(self, data):
        self.control_socket.send(data)