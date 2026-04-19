"""
WebSocket 认证中间件
支持从 URL 查询参数中获取 JWT Token 或 sessionid
"""
from urllib.parse import parse_qs
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async


class QueryAuthMiddleware:
    """
    自定义认证中间件，支持从 URL 查询参数中获取 JWT Token 或 sessionid
    
    用法:
        application = ProtocolTypeRouter({
            "websocket": QueryAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            ),
        })
    """
    
    def __init__(self, inner):
        self.inner = inner
    
    async def __call__(self, scope, receive, send):
        # 从 URL 查询参数中获取 token 或 sessionid
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        user = None
        
        # 优先尝试 JWT Token 认证
        if 'token' in query_params:
            token = query_params['token'][0]
            user = await self.get_user_from_jwt(token)
        
        # 如果没有 token，尝试 sessionid 认证
        if not user or user.is_anonymous:
            if 'sessionid' in query_params:
                session_key = query_params['sessionid'][0]
                user = await self.get_user_from_session(session_key)
        
        # 如果认证成功，设置用户
        if user and not user.is_anonymous:
            scope['user'] = user
        
        return await self.inner(scope, receive, send)
    
    @sync_to_async
    def get_user_from_jwt(self, token):
        """从 JWT Token 获取用户"""
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # 验证 token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            # 获取用户
            return User.objects.get(id=user_id)
        except Exception as e:
            print(f"JWT authentication error: {e}")
            return AnonymousUser()
    
    @sync_to_async
    def get_user_from_session(self, session_key):
        """从 session key 获取用户"""
        try:
            from django.contrib.auth import get_user_model
            from django.contrib.sessions.models import Session
            
            User = get_user_model()
            
            # 获取 session
            session = Session.objects.get(session_key=session_key)
            session_data = session.get_decoded()
            
            # 从 session 数据中获取用户 ID
            user_id = session_data.get('_auth_user_id')
            
            if user_id:
                return User.objects.get(pk=user_id)
            
            return AnonymousUser()
        except Exception as e:
            print(f"Session authentication error: {e}")
            return AnonymousUser()


# 包装函数，方便使用
def QueryAuthMiddlewareStack(inner):
    """
    结合 QueryAuthMiddleware 和 AuthMiddlewareStack
    
    优先使用 URL 参数中的 token/sessionid，如果没有则使用 Cookie
    """
    return QueryAuthMiddleware(AuthMiddlewareStack(inner))
