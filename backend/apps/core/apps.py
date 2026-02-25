"""
Core应用配置
在应用启动时加载配置文件
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = '核心模块'
    
    def ready(self):
        """应用启动时执行"""
        logger.info('Core应用启动，开始加载配置...')
        
        # 导入配置管理器
        from .management.commands.load_config import config_manager
        
        # 加载配置
        config_manager.load_config()
        
        # 记录配置信息
        server_config = config_manager.get_server_config()
        logger.info(f'服务器配置已加载: {server_config}')
        
        logger.info('Core应用启动完成')