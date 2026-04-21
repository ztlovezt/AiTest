from rest_framework import generics, status, permissions, exceptions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from .models import User, UserProfile
from .serializers import UserSerializer, UserCreateSerializer, LoginSerializer, UserProfileSerializer

# JWT 相关导入
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 安全地创建token
        try:
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)
            token_key = token.key
        except ImportError:
            token_key = f"temp_token_{user.id}"
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token_key
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def login_view(request):
    try:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)

        # JWT Token (优先使用JWT)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # 获取token过期时间配置
        access_token_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']

        return Response({
            'user': UserSerializer(user).data,
            'access': access_token,
            'refresh': refresh_token,
            'access_expires_in': int(access_token_lifetime.total_seconds()),
            'refresh_expires_in': int(refresh_token_lifetime.total_seconds()),
            'message': '登录成功'
        })
    except exceptions.ValidationError as e:
        # 处理验证错误（如用户名或密码错误）
        error_message = None
        if hasattr(e, 'detail'):
            if isinstance(e.detail, dict):
                # 检查 non_field_errors
                if 'non_field_errors' in e.detail:
                    errors = e.detail['non_field_errors']
                    if errors and len(errors) > 0:
                        error_message = str(errors[0])
                # 检查其他字段错误
                else:
                    for field, errors in e.detail.items():
                        if errors and len(errors) > 0:
                            error_message = str(errors[0])
                            break
            elif isinstance(e.detail, list):
                error_message = str(e.detail[0])
            else:
                error_message = str(e.detail)
        
        return Response({
            'error': error_message or '用户名或密码错误',
            'message': '登录失败'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            'error': str(e),
            'message': '登录失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def token_refresh_view(request):
    """自定义 Token 刷新接口，返回过期时间"""
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
    
    refresh_token = request.data.get('refresh')
    
    if not refresh_token:
        return Response({
            'error': 'refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        
        # 生成新的 access token
        access_token = str(refresh.access_token)
        
        # 获取过期时间配置
        access_token_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        
        response_data = {
            'access': access_token,
            'access_expires_in': int(access_token_lifetime.total_seconds()),
        }
        
        # 如果启用了 token 轮换，生成新的 refresh token
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(refresh.user)
            response_data['refresh'] = str(new_refresh)
        
        return Response(response_data)
        
    except (TokenError, InvalidToken) as e:
        return Response({
            'error': 'invalid or expired refresh token',
            'detail': str(e)
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@csrf_exempt
def logout_view(request):
    """用户退出登录，将refresh token加入黑名单"""
    if request.user.is_authenticated:
        try:
            # 尝试将refresh token加入黑名单
            refresh_token = request.data.get('refresh')
            if refresh_token:
                from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
                from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
                try:
                    token = JWTRefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    print(f"Blacklist error: {e}")
        except Exception as e:
            print(f"Logout error: {e}")

        # 清除旧的auth token（向后兼容）
        try:
            request.user.auth_token.delete()
        except:
            pass

        logout(request)

    return Response({'message': '退出成功'})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """修改密码"""
    from django.contrib.auth import authenticate
    from django.contrib.auth.hashers import make_password
    
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response({
            'error': '当前密码和新密码不能为空'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if len(new_password) < 6:
        return Response({
            'error': '新密码长度不能少于6位'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = request.user
    
    if not user.check_password(current_password):
        return Response({
            'error': '当前密码错误'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if user.check_password(new_password):
        return Response({
            'error': '新密码不能与当前密码相同'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': '密码修改成功'})


@api_view(['GET'])
def profile_view(request):
    if not request.user.is_authenticated:
        return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
