"""
TestHub 后端启动脚本（支持 WebSocket）
- 开发测试阶段使用
- 自动使用 config.yaml 中配置的端口
- 使用 Daphne ASGI 服务器支持 WebSocket
- 同时启动 Django-Q 任务队列
"""
import os
import sys
import yaml
import subprocess
import signal
import time
import platform

# 读取 config.yaml 中的端口配置
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        backend_port = config.get('server', {}).get('backend_port', 8000)
except Exception as e:
    print(f"读取配置文件失败: {e}")
    print(f"配置文件路径: {config_path}")
    backend_port = 8000

print("=" * 60)
print("   TestHub Backend Server (with WebSocket Support)")
print("   Using Daphne ASGI Server")
print("=" * 60)
print()
print(f"后端端口: {backend_port}")
print(f"WebSocket 支持: 已启用")
print()

# 获取 manage.py 和 asgi.py 的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
manage_py_path = os.path.join(script_dir, 'manage.py')
asgi_app = 'backend.asgi:application'

# 子进程列表
processes = []

# 信号处理函数
def cleanup(signum=None, frame=None):
    """关闭所有子进程"""
    print("\n正在关闭服务...")
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("服务已关闭")
    sys.exit(0)

# 注册信号处理器
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# 检查是否为 Windows 系统
is_windows = platform.system() == 'Windows'

if is_windows:
    # Windows 系统使用 Daphne
    print("检测到 Windows 系统，使用 Daphne 启动...")
    print()
    
    # 启动 Daphne 服务器（支持 WebSocket）
    proc_server = subprocess.Popen(
        [sys.executable, '-m', 'daphne', '-b', '0.0.0.0', '-p', str(backend_port), asgi_app],
        creationflags=subprocess.CREATE_NEW_CONSOLE if is_windows else 0
    )
    processes.append(proc_server)
    print(f"✓ Daphne 服务器已启动 (端口: {backend_port})")
else:
    # Linux/Mac 系统也使用 Daphne（推荐）
    print("使用 Daphne ASGI 服务器启动...")
    print()
    
    # 启动 Daphne 服务器（支持 WebSocket）
    proc_server = subprocess.Popen(
        [sys.executable, '-m', 'daphne', '-b', '0.0.0.0', '-p', str(backend_port), asgi_app]
    )
    processes.append(proc_server)
    print(f"✓ Daphne 服务器已启动 (端口: {backend_port})")

print()

# 启动 Django-Q 任务队列
print("正在启动 Django-Q 任务队列...")
proc_queue = subprocess.Popen([sys.executable, manage_py_path, 'qcluster'])
processes.append(proc_queue)
print("✓ Django-Q 任务队列已启动")

print()
print("=" * 60)
print("服务启动完成！")
print(f"后端地址: http://127.0.0.1:{backend_port}")
print(f"WebSocket: ws://127.0.0.1:{backend_port}/ws/...")
print("按 Ctrl+C 停止服务")
print("=" * 60)
print()

# 监控进程状态
while True:
    time.sleep(1)
    for proc in processes:
        if proc.poll() is not None and proc.returncode != 0:
            print(f"\n进程异常退出: {proc.args}")
            print(f"返回码：{proc.returncode}")
            cleanup()
