# -*- coding: utf-8 -*-
import logging
from .scrcpy_manager import ScrcpyManager

logger = logging.getLogger(__name__)

class ScrcpyPool:
    """
    Scrcpy 服务池 (单例)
    管理所有设备的 ScrcpyManager 实例，实现服务持久化
    """
    _instance = None
    _managers = {}  # device_id -> ScrcpyManager

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScrcpyPool, cls).__new__(cls)
        return cls._instance

    def get_manager(self, device_id, adb_path='adb'):
        """获取或创建设备的 ScrcpyManager"""
        if device_id not in self._managers:
            logger.info(f"为设备 {device_id} 创建新的 ScrcpyManager")
            self._managers[device_id] = ScrcpyManager(device_id, adb_path)
        return self._managers[device_id]

    def stop_all(self):
        """停止所有服务"""
        for device_id, manager in self._managers.items():
            logger.info(f"停止设备 {device_id} 的 Scrcpy 服务")
            manager.stop()
        self._managers.clear()

    def remove_manager(self, device_id):
        """移除并停止特定设备的服务"""
        if device_id in self._managers:
            self._managers[device_id].stop()
            del self._managers[device_id]

# 全局单例
scrcpy_pool = ScrcpyPool()
