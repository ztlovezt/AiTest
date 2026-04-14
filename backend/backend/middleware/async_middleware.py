"""异步中间件"""
import time
import logging
import asyncio
from django.utils.deprecation import MiddlewareMixin
from asgiref.sync import sync_to_async
from django.conf import settings

logger = logging.getLogger(__name__)


class AsyncRequestTimingMiddleware(MiddlewareMixin):
    """请求计时中间件 - 支持同步和异步"""
    
    SLOW_REQUEST_THRESHOLD = 1000
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # 如果 response 是协程（异步环境），需要等待
        if asyncio.iscoroutine(response):
            # 在异步环境中，我们不能直接修改响应头
            # 需要在协程完成后处理，这里简化处理
            async def process_response():
                resp = await response
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 只有当 resp 是 HttpResponse 对象时才添加头
                if hasattr(resp, '__setitem__'):
                    resp['X-Response-Time'] = f'{response_time:.2f}ms'
                    self._save_performance_log(request, resp, response_time)
                
                return resp
            
            return process_response()
        else:
            # 同步环境
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            response['X-Response-Time'] = f'{response_time:.2f}ms'
            
            self._save_performance_log(request, response, response_time)
            
            return response
    
    def _save_performance_log(self, request, response, response_time):
        """保存性能日志到数据库 - 支持异步环境"""
        try:
            if request.path.startswith('/admin/') or request.path.startswith('/static/'):
                return
            
            if request.path.startswith('/api/') or request.path.startswith('/ws/'):
                from apps.core.models import RequestPerformanceLog
                
                user = None
                if hasattr(request, 'user') and request.user.is_authenticated:
                    user = request.user
                
                ip_address = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                # 检查是否在异步上下文中
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 在异步上下文中，使用 sync_to_async
                        async def save_log_async():
                            @sync_to_async
                            def create_log():
                                return RequestPerformanceLog.objects.create(
                                    path=request.path[:500],
                                    method=request.method,
                                    response_time=response_time,
                                    status_code=response.status_code,
                                    user=user,
                                    ip_address=ip_address,
                                    user_agent=user_agent
                                )
                            return await create_log()
                        
                        # 创建任务但不等待（fire-and-forget）
                        asyncio.create_task(save_log_async())
                        
                        if response_time > self.SLOW_REQUEST_THRESHOLD:
                            logger.warning(
                                f"慢请求: {request.method} {request.path} - {response_time:.2f}ms"
                            )
                        return
                except RuntimeError:
                    # 没有运行中的事件循环，使用同步方式
                    pass
                
                # 同步环境或无法检测时，直接调用
                RequestPerformanceLog.objects.create(
                    path=request.path[:500],
                    method=request.method,
                    response_time=response_time,
                    status_code=response.status_code,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if response_time > self.SLOW_REQUEST_THRESHOLD:
                    logger.warning(
                        f"慢请求: {request.method} {request.path} - {response_time:.2f}ms"
                    )
        except Exception as e:
            logger.error(f"保存性能日志失败: {e}")
    
    def _get_client_ip(self, request):
        """获取客户端IP地址"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
