from django.apps import AppConfig


class PrecisionTestingConfig(AppConfig):
    """精准测试应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.precision_testing'
    verbose_name = '精准测试'

    def ready(self):
        """应用启动时验证 Neo4j 连接"""
        try:
            from .neo4j_client import Neo4jClient
            client = Neo4jClient()
            client.verify_connectivity()
        except Exception:
            # 启动时不阻断,仅在日志记录
            import logging
            logging.getLogger(__name__).warning(
                "Neo4j 连接未就绪,精准测试图数据库功能暂不可用"
            )
