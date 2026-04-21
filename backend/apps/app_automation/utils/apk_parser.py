# -*- coding: utf-8 -*-
"""
APK 文件解析工具
用于从 APK 文件中提取应用信息（包名、版本等）
"""
import os
import subprocess
import tempfile
import zipfile
from loguru import logger


def extract_apk_info(apk_path: str) -> dict:
    """
    从 APK 文件中提取应用信息
    
    Args:
        apk_path: APK 文件路径
        
    Returns:
        包含应用信息的字典，如：
        {
            'package_name': 'com.example.app',
            'version_name': '1.0.0',
            'version_code': '1',
            'app_name': 'Example App'
        }
    """
    result = {
        'package_name': '',
        'version_name': '',
        'version_code': '',
        'app_name': ''
    }
    
    try:
        # 方法1: 使用 aapt (Android Asset Packaging Tool)
        package_info = _extract_with_aapt(apk_path)
        if package_info and package_info.get('package_name'):
            result.update(package_info)
            logger.info(f"成功使用 aapt 提取 APK 信息: {result}")
            return result
        
        # 方法2: 直接解析 AndroidManifest.xml（ZIP 格式）
        package_info = _extract_from_manifest(apk_path)
        if package_info and package_info.get('package_name'):
            result.update(package_info)
            logger.info(f"成功从 Manifest 提取 APK 信息: {result}")
            return result
            
        logger.warning(f"无法从 APK 文件中提取包名: {apk_path}")
        
    except Exception as e:
        logger.error(f"提取 APK 信息失败: {str(e)}", exc_info=True)
    
    return result


def _extract_with_aapt(apk_path: str) -> dict:
    """
    使用 aapt 工具提取 APK 信息
    
    Args:
        apk_path: APK 文件路径
        
    Returns:
        应用信息字典
    """
    try:
        # 尝试多个可能的 aapt 路径
        aapt_paths = [
            'aapt',  # 系统 PATH 中
            os.path.join(os.environ.get('ANDROID_HOME', ''), 'build-tools', '34.0.0', 'aapt'),
            os.path.join(os.environ.get('ANDROID_HOME', ''), 'build-tools', '33.0.0', 'aapt'),
        ]
        
        aapt_cmd = None
        for path in aapt_paths:
            if os.path.exists(path) or _is_command_available(path):
                aapt_cmd = path
                break
        
        if not aapt_cmd:
            logger.warning("未找到 aapt 工具")
            return {}
        
        # 执行 aapt dump badging
        cmd = [aapt_cmd, 'dump', 'badging', apk_path]
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if process.returncode != 0:
            logger.warning(f"aapt 执行失败: {process.stderr}")
            return {}
        
        output = process.stdout
        info = {}
        
        # 解析包名
        for line in output.split('\n'):
            if line.startswith('package:'):
                # package: name='com.example.app' versionCode='1' versionName='1.0'
                parts = line.split()
                for part in parts:
                    if part.startswith("name='"):
                        info['package_name'] = part.split("'")[1]
                    elif part.startswith("versionName='"):
                        info['version_name'] = part.split("'")[1]
                    elif part.startswith("versionCode='"):
                        info['version_code'] = part.split("'")[1]
            
            elif line.startswith('application-label:'):
                # application-label:'Example App'
                info['app_name'] = line.split("'", 1)[1].rsplit("'", 1)[0]
        
        return info
        
    except subprocess.TimeoutExpired:
        logger.error("aapt 执行超时")
        return {}
    except Exception as e:
        logger.error(f"aapt 提取失败: {str(e)}")
        return {}


def _extract_from_manifest(apk_path: str) -> dict:
    """
    直接从 APK 的 AndroidManifest.xml 中提取信息
    使用 androguard 库进行解析
    
    Args:
        apk_path: APK 文件路径
        
    Returns:
        应用信息字典
    """
    try:
        # 尝试使用 androguard 解析
        try:
            from androguard.core import apk as apk_module
            
            logger.info(f"使用 androguard 解析 APK: {apk_path}")
            apk_obj = apk_module.APK(apk_path)
            
            if apk_obj.is_valid_APK():
                info = {
                    'package_name': apk_obj.get_package(),
                    'version_name': apk_obj.get_androidversion_name() or '',
                    'version_code': str(apk_obj.get_androidversion_code()) if apk_obj.get_androidversion_code() else '',
                    'app_name': apk_obj.get_app_name() or ''
                }
                
                logger.info(f"成功使用 androguard 提取 APK 信息: {info}")
                return info
            else:
                logger.warning("APK 文件无效")
                return {}
                
        except ImportError as e:
            logger.warning(f"androguard 库导入失败: {str(e)}")
            logger.info("建议安装: pip install androguard")
            return {}
        except Exception as e:
            logger.error(f"androguard 解析失败: {str(e)}", exc_info=True)
            return {}
            
    except Exception as e:
        logger.error(f"从 Manifest 提取信息失败: {str(e)}")
        return {}


def _is_command_available(cmd: str) -> bool:
    """
    检查命令是否可用
    
    Args:
        cmd: 命令名称
        
    Returns:
        是否可用
    """
    try:
        subprocess.run(
            [cmd, '--version'],
            capture_output=True,
            timeout=5
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def validate_apk_file(file_path: str) -> tuple:
    """
    验证 APK 文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        (是否有效, 错误消息)
    """
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not file_path.lower().endswith('.apk'):
        return False, "文件扩展名不是 .apk"
    
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "文件大小为 0"
    
    if file_size > 500 * 1024 * 1024:  # 500MB
        return False, "文件大小超过限制（500MB）"
    
    # 尝试验证 ZIP 格式
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            # 检查是否包含必要的文件
            names = z.namelist()
            if 'AndroidManifest.xml' not in names:
                return False, "无效的 APK 文件：缺少 AndroidManifest.xml"
    except zipfile.BadZipFile:
        return False, "无效的 APK 文件格式"
    
    return True, ""
