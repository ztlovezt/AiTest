from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DifyConfig
from .serializers import DifyConfigSerializer
import requests


class DifyConfigViewSet(viewsets.ModelViewSet):
    """Dify配置管理ViewSet"""
    queryset = DifyConfig.objects.all()
    serializer_class = DifyConfigSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """获取激活的配置"""
        active_config = DifyConfig.get_active_config()
        if active_config:
            serializer = self.get_serializer(active_config)
            data = serializer.data
            if 'api_key' in data and data['api_key']:
                data['api_key_masked'] = data['api_key'][:8] + '****'
                del data['api_key']
            data['configured'] = True
            return Response(data)
        return Response({
            'configured': False,
            'id': None,
            'api_url': '',
            'api_key_masked': '',
            'is_active': False,
            'message': '未找到激活的配置'
        }, status=status.HTTP_200_OK)
    
    def create(self, request):
        """创建新配置"""
        # 如果设置为激活，先将其他配置设为不激活
        if request.data.get('is_active', True):
            DifyConfig.objects.update(is_active=False)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, pk=None, partial=False):
        """更新配置"""
        instance = self.get_object()
        
        # 如果设置为激活，先将其他配置设为不激活
        if request.data.get('is_active', False):
            DifyConfig.objects.exclude(pk=pk).update(is_active=False)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        """部分更新配置"""
        return self.update(request, pk=pk, partial=True)
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """测试Dify API连接"""
        api_url = request.data.get('api_url')
        api_key = request.data.get('api_key')
        
        # 如果前端没有提供api_key，尝试从数据库获取现有的配置进行测试
        if not api_key:
            active_config = DifyConfig.get_active_config()
            if active_config and active_config.api_url == api_url:
                api_key = active_config.api_key
        
        if not api_url or not api_key:
            return Response(
                {'error': 'API URL和API Key都是必填项'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 发送测试请求到Dify API
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 去除URL末尾的斜杠
            api_url = api_url.rstrip('/')
            
            # 使用一个简单的测试消息，假设是 Chat App 类型
            test_data = {
                'inputs': {},
                'query': 'test_connection',
                'user': 'system_test'
            }
            
            response = requests.post(
                f'{api_url}/chat-messages',
                headers=headers,
                json=test_data,
                timeout=15
            )
            
            if response.status_code == 200:
                return Response({'message': '连接成功！', 'success': True})
            elif response.status_code == 401:
                return Response({'error': '连接失败: API Key 无效或未授权', 'success': False}, status=status.HTTP_400_BAD_REQUEST)
            elif response.status_code == 404:
                return Response({'error': '连接失败: API URL 不正确 (未找到接口)', 'success': False}, status=status.HTTP_400_BAD_REQUEST)
            elif response.status_code == 400:
                # 收到 400 说明请求已经成功到达Dify且通过了Token鉴权（否则是401）。
                # 这种通常是因为Dify端的应用未绑定模型，或者传入参数不匹配。可以认为“网络连接和鉴权”是成功的。
                error_msg = '连接成功！(提示: Dify端的应用模型可能未配置完善)'
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = f"连接成功！(提示: {error_data['message']})"
                except:
                    pass
                # 依然返回 success=True，允许用户保存配置
                return Response({'message': error_msg, 'success': True})
            else:
                return Response({
                    'error': f'连接异常: {response.status_code}',
                    'detail': response.text,
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except requests.exceptions.Timeout:
            return Response({
                'error': '连接超时，请检查API URL是否正确',
                'success': False
            }, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'连接错误: {str(e)}',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)
