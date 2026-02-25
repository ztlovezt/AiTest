"""
TestHub 后端启动脚本
自动使用 config.yaml 中配置的端口
"""
import os
import sys
import yaml
import subprocess

# 读取 config.yaml 中的端口配置
config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')

try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        backend_port = config.get('server', {}).get('backend_port', 8000)
    # print(f"成功读取配置文件: {config_path}")
    # print(f"配置内容: {config}")
except Exception as e:
    print(f"读取配置文件失败: {e}")
    print(f"配置文件路径: {config_path}")
    backend_port = 8000

print(f"正在启动后端服务器，端口: {backend_port}")

# 启动服务器
subprocess.run([sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{backend_port}'])