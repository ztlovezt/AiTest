"""
ASGI config for backend project.
支持 Daphne (WebSocket) 和 runserver (仅 HTTP) 两种模式
"""

import os
import logging
import sys
import asyncio

# 修复 Windows 环境下 asyncio 子进程的 NotImplementedError
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from apps.app_automation import routing as app_automation_routing
    from .websocket_auth import QueryAuthMiddlewareStack

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": QueryAuthMiddlewareStack(
            URLRouter(app_automation_routing.websocket_urlpatterns)
        ),
    })
    logger.info("ASGI 已启用 WebSocket 支持 (需通过 Daphne 启动)")
except ImportError:
    application = django_asgi_app
    logger.warning("channels 未安装，WebSocket 不可用，仅支持 HTTP")
except Exception as e:
    application = django_asgi_app
    logger.warning(f"WebSocket 初始化失败: {e}，降级为仅 HTTP 模式")