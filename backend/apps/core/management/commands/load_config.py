"""
配置管理服务
用于管理系统配置，确保系统启动时读取config.yaml中的配置
"""
import os
import yaml
import logging
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理类"""
    
    def __init__(self):
        self.config_file = None
        self.config = {}
        self._initialize()
    
    def _initialize(self):
        """初始化配置管理器"""
        # 查找config.yaml文件
        self._find_config_file()
        # 加载配置
        self.load_config()
    
    def _find_config_file(self):
        """查找config.yaml文件"""
        # 从项目根目录开始查找
        current_path = Path(__file__).resolve().parent.parent.parent.parent
        
        while current_path != current_path.parent:
            config_path = current_path / 'config.yaml'
            if config_path.exists():
                self.config_file = config_path
                logger.info(f"找到配置文件: {self.config_file}")
                break
            current_path = current_path.parent
        else:
            # 如果没找到，使用默认位置
            default_path = Path(__file__).resolve().parent.parent.parent.parent / 'config.yaml'
            self.config_file = default_path
            logger.warning(f"未找到配置文件，使用默认位置: {self.config_file}")
    
    def load_config(self):
        """加载配置文件"""
        if not self.config_file or not self.config_file.exists():
            logger.error(f"配置文件不存在: {self.config_file}")
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {self.config_file}")
            logger.debug(f"配置内容: {self.config}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config = {}
    
    def get(self, key_path, default=None, cast=None):
        """获取配置值"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        # 类型转换
        if cast is not None and value is not None:
            try:
                return cast(value)
            except (ValueError, TypeError):
                return default
        
        return value
    
    def get_server_config(self):
        """获取服务器配置"""
        return self.config.get('server', {})
    
    def get_database_config(self):
        """获取数据库配置"""
        return self.config.get('database', {})
    
    def get_redis_config(self):
        """获取Redis配置"""
        return self.config.get('redis', {})
    
    def get_cache_config(self):
        """获取缓存配置"""
        return self.config.get('cache', {})
    
    def get_logging_config(self):
        """获取日志配置"""
        return self.config.get('logging', {})
    
    def get_jwt_config(self):
        """获取JWT配置"""
        return self.config.get('jwt', {})
    
    def get_throttling_config(self):
        """获取速率限制配置"""
        return self.config.get('throttling', {})
    
    def get_cors_config(self):
        """获取CORS配置"""
        return self.config.get('cors', {})
    
    def get_email_config(self):
        """获取邮件配置"""
        return self.config.get('email', {})
    
    def get_scheduler_config(self):
        """获取定时任务配置"""
        return self.config.get('scheduler', {})
    
    def get_upload_config(self):
        """获取文件上传配置"""
        return self.config.get('upload', {})
    
    def get_allure_config(self):
        """获取Allure配置"""
        return self.config.get('allure', {})
    
    def update_config(self, new_config):
        """更新配置"""
        self.config.update(new_config)
        logger.info("配置已更新")
    
    def save_config(self):
        """保存配置到文件"""
        if not self.config_file:
            logger.error("配置文件路径未设置")
            return False
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False


# 创建全局配置管理器实例
config_manager = ConfigManager()


class Command(BaseCommand):
    """管理命令：加载配置"""
    help = '加载配置文件并更新系统配置'
    
    def handle(self, *args, **options):
        self.stdout.write('开始加载配置文件...')
        
        # 显示配置文件路径
        self.stdout.write(f'配置文件路径: {config_manager.config_file}')
        
        # 加载配置
        config_manager.load_config()
        
        # 显示配置信息
        server_config = config_manager.get_server_config()
        self.stdout.write(f'服务器配置: {server_config}')
        
        database_config = config_manager.get_database_config()
        self.stdout.write(f'数据库配置: {database_config}')
        
        # 显示具体的端口配置
        frontend_port = config_manager.get('server.frontend_port', 3000)
        backend_port = config_manager.get('server.backend_port', 8000)
        self.stdout.write(f'前端端口: {frontend_port}')
        self.stdout.write(f'后端端口: {backend_port}')
        
        self.stdout.write('配置加载完成！')