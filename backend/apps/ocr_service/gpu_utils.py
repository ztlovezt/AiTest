# -*- coding: utf-8 -*-
"""
GPU 可用性检测工具
"""
import os
import subprocess
import sys
from typing import Dict, Any, Optional, Tuple

from backend.log_config import get_logger

logger = get_logger(__name__)


def check_cuda_available() -> Tuple[bool, str]:
    """
    检查 CUDA 是否可用
    
    Returns:
        (是否可用, 详细信息)
    """
    try:
        import paddle
        if paddle.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            if gpu_count > 0:
                gpu_name = paddle.device.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                return True, f"检测到 {gpu_count} 个 GPU: {gpu_name}"
            else:
                return False, "CUDA 已编译但未检测到 GPU 设备"
        else:
            return False, "PaddlePaddle 未使用 CUDA 编译"
    except ImportError:
        return False, "PaddlePaddle 未安装"
    except Exception as e:
        return False, f"CUDA 检测失败: {str(e)}"


def check_paddle_gpu_installed() -> Tuple[bool, str]:
    """
    检查是否安装了 GPU 版本的 PaddlePaddle
    
    Returns:
        (是否安装, 详细信息)
    """
    try:
        import paddle
        version = paddle.__version__
        
        try:
            if paddle.is_compiled_with_cuda():
                return True, f"PaddlePaddle-GPU {version} 已安装"
            else:
                return False, f"PaddlePaddle {version} 是 CPU 版本，需要安装 GPU 版本"
        except:
            return False, f"PaddlePaddle {version} 是 CPU 版本"
            
    except ImportError:
        return False, "PaddlePaddle 未安装"


def check_nvidia_driver() -> Tuple[bool, str]:
    """
    检查 NVIDIA 驱动是否安装
    
    Returns:
        (是否安装, 详细信息)
    """
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info = result.stdout.strip()
                return True, f"NVIDIA 驱动已安装: {info}"
            else:
                return False, "nvidia-smi 命令执行失败，可能未安装 NVIDIA 驱动"
        else:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                info = result.stdout.strip()
                return True, f"NVIDIA 驱动已安装: {info}"
            else:
                return False, "nvidia-smi 命令执行失败"
    except FileNotFoundError:
        return False, "未找到 nvidia-smi 命令，请安装 NVIDIA 驱动"
    except subprocess.TimeoutExpired:
        return False, "nvidia-smi 命令超时"
    except Exception as e:
        return False, f"NVIDIA 驱动检测失败: {str(e)}"


def get_gpu_info() -> Dict[str, Any]:
    """
    获取 GPU 详细信息
    
    Returns:
        GPU 信息字典
    """
    info = {
        'nvidia_driver': {
            'available': False,
            'message': ''
        },
        'paddle_gpu': {
            'available': False,
            'message': ''
        },
        'cuda': {
            'available': False,
            'message': ''
        },
        'gpu_available': False,
        'gpu_name': None,
        'gpu_count': 0,
        'cuda_version': None,
        'install_command': None,
    }
    
    info['nvidia_driver']['available'], info['nvidia_driver']['message'] = check_nvidia_driver()
    
    info['paddle_gpu']['available'], info['paddle_gpu']['message'] = check_paddle_gpu_installed()
    
    info['cuda']['available'], info['cuda']['message'] = check_cuda_available()
    
    try:
        import paddle
        if paddle.is_compiled_with_cuda():
            info['gpu_count'] = paddle.device.cuda.device_count()
            if info['gpu_count'] > 0:
                info['gpu_name'] = paddle.device.cuda.get_device_name(0)
                info['gpu_available'] = True
    except:
        pass
    
    if not info['paddle_gpu']['available']:
        info['install_command'] = get_paddle_gpu_install_command()
    
    return info


def get_paddle_gpu_install_command() -> str:
    """
    获取 PaddlePaddle GPU 版本安装命令
    
    Returns:
        安装命令
    """
    import platform
    
    system = platform.system().lower()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    if system == 'windows':
        return f"python -m pip install paddlepaddle-gpu -i https://mirror.baidu.com/pypi/simple"
    elif system == 'linux':
        return f"python -m pip install paddlepaddle-gpu -i https://mirror.baidu.com/pypi/simple"
    else:
        return "pip install paddlepaddle-gpu"


def check_gpu_requirements() -> Dict[str, Any]:
    """
    检查 GPU 加速的所有要求
    
    Returns:
        检查结果
    """
    result = {
        'can_use_gpu': False,
        'issues': [],
        'warnings': [],
        'install_command': None,
    }
    
    nvidia_ok, nvidia_msg = check_nvidia_driver()
    if not nvidia_ok:
        result['issues'].append({
            'type': 'nvidia_driver',
            'message': nvidia_msg,
            'solution': '请安装 NVIDIA 显卡驱动'
        })
    
    paddle_gpu_ok, paddle_gpu_msg = check_paddle_gpu_installed()
    if not paddle_gpu_ok:
        result['issues'].append({
            'type': 'paddle_gpu',
            'message': paddle_gpu_msg,
            'solution': '请安装 GPU 版本的 PaddlePaddle'
        })
        result['install_command'] = get_paddle_gpu_install_command()
    
    cuda_ok, cuda_msg = check_cuda_available()
    if not cuda_ok:
        result['warnings'].append({
            'type': 'cuda',
            'message': cuda_msg
        })
    
    result['can_use_gpu'] = nvidia_ok and paddle_gpu_ok and cuda_ok
    
    return result
