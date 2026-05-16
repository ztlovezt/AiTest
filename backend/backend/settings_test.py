"""
测试专用 Django Settings
继承主配置，覆盖数据库为 SQLite 内存数据库，避免 MySQL 迁移冲突
"""
from backend.settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': True,
    }
}

# 测试时禁用 Neo4j 连接检查（避免连接失败阻塞启动）
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')  # noqa: F405

# 测试时禁用某些中间件/应用可能的问题
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ['channels']]  # noqa: F405

# 禁用导致测试超时的异步中间件
MIDDLEWARE = [m for m in MIDDLEWARE if m != 'backend.middleware.async_middleware.AsyncRequestTimingMiddleware']  # noqa: F405

# 允许 testserver 用于 Django test client
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
