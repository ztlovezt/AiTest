"""
Loguru日志配置模块，提供统一的日志接口
"""
import sys
import os
from pathlib import Path

from loguru import logger

from .config_loader import config_loader

logging_config = config_loader.get_logging_config()

def exclude_errors(record):
    """过滤器：过滤掉 ERROR 级别的日志"""
    return record["level"].name != "ERROR"


def only_errors(record):
    """过滤器：只记录 ERROR 级别的日志"""
    return record["level"].name == "ERROR"


class LogConfig:
    """Loguru日志配置类"""
    
    def __init__(self):
        """初始化日志配置"""
        self.log_dir = self._get_log_dir()
        self.log_format = self._get_log_format()
        self.debug_enabled = self._get_debug_enabled()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._configure_logger()
    
    def _get_log_dir(self):
        """获取日志目录"""
        try:
            log_dir_config = logging_config.get('dir', 'logs')
            
            if os.path.isabs(log_dir_config):
                return Path(log_dir_config)
            else:
                project_root = str(config_loader.project_root)
                return Path(os.path.join(project_root, log_dir_config))
        except Exception as e:
            logger.warning(f"读取日志配置失败，使用默认目录: {e}")
            return Path('logs')
    
    def _get_debug_enabled(self):
        """获取是否启用DEBUG日志"""
        try:
            return logging_config.get('debug_enabled', False)
        except Exception as e:
            logger.warning(f"读取DEBUG配置失败，默认关闭DEBUG日志: {e}")
            return False
    
    def _get_log_format(self):
        """获取日志格式"""
        try:
            format_config = logging_config.get('format', None)
            
            if format_config:
                return format_config
            else:
                return "{time:YYYY-MM-DD HH:mm:ss.SSS} - [{name}-->{function}:{line}] - {level} - {message}"
        except Exception as e:
            logger.warning(f"读取日志格式配置失败，使用默认格式: {e}")
            return "{time:YYYY-MM-DD HH:mm:ss.SSS} - [{name}-->{function}:{line}] - {level} - {message}"
    
    def _configure_logger(self):
        """配置loguru logger"""
        logger.remove()  # 移除默认的handler
        
        # 根据配置决定控制台日志级别
        console_level = "DEBUG" if self.debug_enabled else "INFO"
        
        # 控制台输出 - 详细格式（带颜色）
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> - <cyan>[{name}-->{function}:{line}]</cyan> - <level>{level}</level> - <level>{message}</level>",
            level=console_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
            enqueue=True  # 异步写入，避免阻塞
        )
        
        # 主日志文件 - 保留7天（不包含 ERROR 级别的日志）
        logger.add(
            self.log_dir / "app.log",
            rotation="00:00",  # 每天午夜轮转
            retention="7 days",  # 保留7天
            compression="zip",  # 自动压缩旧日志
            encoding="utf-8",
            level="INFO",
            format=self.log_format,
            filter=exclude_errors,  # 过滤掉 ERROR 级别的日志
            backtrace=True,
            diagnose=True,
            enqueue=True  # 异步写入
        )
        
        # 错误日志文件 - 保留7天（只记录 ERROR 级别的日志）
        logger.add(
            self.log_dir / "error.log",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            level="ERROR",
            format=self.log_format,
            filter=only_errors,  # 只记录 ERROR 级别的日志
            backtrace=True,
            diagnose=True,
            enqueue=True  # 异步写入
        )
        
        # ORM SQL日志文件 - 保留7天（仅在debug_enabled为True时记录DEBUG日志）
        if self.debug_enabled:
            logger.add(
                self.log_dir / "orm_sql.log",
                rotation="00:00",
                retention="7 days",
                compression="zip",
                encoding="utf-8",
                level="DEBUG",
                format=self.log_format,
                backtrace=True,
                diagnose=True,
                enqueue=True
            )
        else:
            logger.add(
                self.log_dir / "orm_sql.log",
                rotation="00:00",
                retention="7 days",
                compression="zip",
                encoding="utf-8",
                level="INFO",
                format=self.log_format,
                backtrace=True,
                diagnose=True,
                enqueue=True
            )
    
    def get_logger(self, name=None):
        """
        获取logger实例
        
        Args:
            name: logger名称（可选）
            
        Returns:
            logger实例
        """
        if name:
            return logger.bind(name=name)
        return logger


# 全局日志配置实例
log_config = LogConfig()


def get_logger(name=None):
    """
    获取logger实例的便捷函数
    
    Args:
        name: logger名称（可选）
        
    Returns:
        logger实例
    """
    return log_config.get_logger(name)


def log_exception(logger, message, *args, **kwargs):
    """
    记录异常日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.exception(message, *args, **kwargs)


def log_error(logger, message, *args, **kwargs):
    """
    记录错误日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.error(message, *args, **kwargs)


def log_warning(logger, message, *args, **kwargs):
    """
    记录警告日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.warning(message, *args, **kwargs)


def log_info(logger, message, *args, **kwargs):
    """
    记录信息日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.info(message, *args, **kwargs)


def log_debug(logger, message, *args, **kwargs):
    """
    记录调试日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.debug(message, *args, **kwargs)


def log_success(logger, message, *args, **kwargs):
    """
    记录成功日志
    
    Args:
        logger: logger实例
        message: 日志消息
        *args: 格式化参数
        **kwargs: 额外字段
    """
    logger.success(message, *args, **kwargs)
