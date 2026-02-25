# https://newpanjing.github.io/simpleui_docs/config.html#%E5%9B%BE%E6%A0%87%E8%AF%B4%E6%98%8E

from pathlib import Path
from decouple import config
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# 导入配置加载器
from .config_loader import config_loader

SECRET_KEY = config('SECRET_KEY', default=config_loader.get('server.secret_key','django-insecure-6wf7pmw0mzh%(^/4%qa/3o5nfg7xmqyi8mewwbyyqmna7ertm5'))

DEBUG = config('DEBUG', default=config_loader.get('server.debug',False), cast=bool)

# ================================
# 服务端口配置
# ================================
# 后端服务端口（开发环境）
BACKEND_PORT = config('BACKEND_PORT', default=config_loader.get('server.backend_port', 8000), cast=int)

# 根据DEBUG模式设置ALLOWED_HOSTS，生产环境不应使用通配符
if DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1',
                           cast=lambda v: [s.strip() for s in v.split(',')])

DJANGO_APPS = [
    'simpleui',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',  # 添加JWT支持
    'rest_framework_simplejwt.token_blacklist',  # JWT token黑名单
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'channels',
]

LOCAL_APPS = [
    'apps.users',
    'apps.projects',
    'apps.testcases',
    'apps.testsuites',
    'apps.executions',
    'apps.reports',
    'apps.reviews',
    'apps.versions',
    'apps.assistant',
    'apps.requirement_analysis',
    'apps.api_testing',
    'apps.ui_automation.apps.UiAutomationConfig',
    'apps.app_automation.apps.AppAutomationConfig',
    'apps.core',
    'apps.data_factory',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'backend.middleware.DisableCSRFMiddleware',  # 添加CSRF禁用中间件
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI_APPLICATION = 'backend.wsgi.application'
ASGI_APPLICATION = 'backend.asgi.application'

db_config = config_loader.get_database_config()
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default=db_config.get('name', 'testhub')),
        'USER': config('DB_USER', default=db_config.get('user', 'test_platform')),
        'PASSWORD': config('DB_PASSWORD', default=db_config.get('password', '')),
        'HOST': config('DB_HOST', default=db_config.get('host', '127.0.0.1')),
        'PORT': config('DB_PORT', default=db_config.get('port', 3306)),
        'OPTIONS': {
            'charset': db_config.get('charset', 'utf8mb4'),
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/
# Supported language codes: 'en-us' (English), 'zh-hans' (Simplified Chinese), 'ja' (Japanese), 'ko' (Korean), etc.
# See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones for timezone list
LANGUAGE_CODE = config('LANGUAGE_CODE', default='zh-hans')
TIME_ZONE = config('TIME_ZONE', default='Asia/Shanghai')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_files')

# 数据工厂的静态文件目录
STATIC_FILES_URL = '/static_files/'
STATIC_FILES_ROOT = os.path.join(BASE_DIR, 'static_files')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# DRF Settings
throttling_config = config_loader.get_throttling_config()
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT认证（优先）
        'rest_framework.authentication.TokenAuthentication',  # 保留Token认证（兼容）
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': throttling_config.get('anon_rate', '100/hour'),
        'user': throttling_config.get('user_rate', '1000/hour')
    },
}

# JWT Settings
from datetime import timedelta

jwt_config = config_loader.get_jwt_config()
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=jwt_config.get('access_token_lifetime', 15)),  # access_token 15分钟（优化安全性）
    'REFRESH_TOKEN_LIFETIME': timedelta(days=jwt_config.get('refresh_token_lifetime', 7)),  # refresh_token 7天
    'ROTATE_REFRESH_TOKENS': jwt_config.get('rotate_refresh_tokens', True),  # 刷新时轮换refresh_token
    'BLACKLIST_AFTER_ROTATION': jwt_config.get('blacklist_after_rotation', True),  # 旧的refresh_token加入黑名单
    'UPDATE_LAST_LOGIN': True,  # 更新最后登录时间

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# CSRF Settings - 根据DEBUG模式设置
if DEBUG:
    CSRF_COOKIE_SECURE = False
    CSRF_USE_SESSIONS = False
    CSRF_COOKIE_HTTPONLY = False
    CSRF_COOKIE_SAMESITE = 'Lax'
else:
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = 'Strict'

# CORS Settings
cors_origins_str = config('CORS_ALLOWED_ORIGINS', default=config_loader.get('cors.allowed_origins',''))
parsed_cors_origins = [s.strip() for s in cors_origins_str.split(',') if s.strip()]

if DEBUG:
    # 开发环境默认允许本地地址，同时合并环境变量里的配置
    # 优先使用环境变量配置的地址，确保服务器IP优先级最高
    CORS_ALLOWED_ORIGINS = [
        *parsed_cors_origins,  # 环境变量配置的地址优先
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    CORS_ALLOW_CREDENTIALS = True
    # 支持EventSource (SSE) 的额外CORS头部
    CORS_ALLOW_HEADERS = [
        'accept',
        'accept-encoding',
        'authorization',
        'content-type',
        'dnt',
        'origin',
        'user-agent',
        'x-csrftoken',
        'x-requested-with',
        'cache-control',  # 添加 SSE 需要的头部
    ]
else:
    # 生产环境 CORS 配置
    if parsed_cors_origins:
        # 如果配置了 CORS_ALLOWED_ORIGINS，使用配置的值
        CORS_ALLOWED_ORIGINS = parsed_cors_origins
    else:
        # 如果未配置，允许所有来源（可根据需求调整）
        CORS_ALLOW_ALL_ORIGINS = True

    CORS_ALLOW_CREDENTIALS = True
    CORS_ALLOW_HEADERS = [
        'accept',
        'accept-encoding',
        'authorization',
        'content-type',
        'dnt',
        'origin',
        'user-agent',
        'x-csrftoken',
        'x-requested-with',
        'cache-control',  # 添加 SSE 需要的头部
    ]
    # SSE 需要的额外配置
    CORS_EXPOSE_HEADERS = ['Content-Type', 'Cache-Control']

# CSRF Settings
CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
]

# Spectacular Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'TestHub API',
    'DESCRIPTION': 'Test Case Management Platform API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # 使用sidecar中的静态文件
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}

# Channels Configuration
if DEBUG:
    # 开发环境使用本地Redis
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': ['redis://127.0.0.1:6379/0'],
            },
        },
    }
else:
    # 生产环境使用配置的Redis
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [config_loader.get('redis.url', 'redis://127.0.0.1:6379/0')],
            },
        },
    }

# Redis配置
# 开发环境和生产环境都使用配置的Redis
REDIS_URL = config('REDIS_URL', default=config_loader.get('redis.url', 'redis://127.0.0.1:6379/0'))

# Celery配置
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Cache配置
# 使用 Redis 缓存（生产环境推荐）
cache_config = config_loader.get_cache_config()
redis_config = config_loader.get_redis_config()

if DEBUG:
    # 开发环境使用本地内存缓存
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'KEY_PREFIX': cache_config.get('key_prefix', 'testhub'),
            'TIMEOUT': cache_config.get('default_timeout', 300),
        }
    }
else:
    # 生产环境使用Redis
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': config_loader.get('redis.url', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': cache_config.get('key_prefix', 'testhub'),
            'TIMEOUT': cache_config.get('default_timeout', 300),
        }
    }

# Session Configuration
# 使用Redis存储会话
if not DEBUG:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

# Email Configuration
email_config = config_loader.get_email_config()
EMAIL_BACKEND = 'apps.api_testing.custom_email_backend.CustomEmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default=email_config.get('host', 'smtp.gmail.com'))
EMAIL_PORT = config('EMAIL_PORT', default=email_config.get('port', 587), cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=email_config.get('use_tls', True), cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=email_config.get('use_ssl', False), cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=email_config.get('host_user', ''))
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=email_config.get('host_password', ''))
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=email_config.get('default_from_email', 'webmaster@localhost'))
EMAIL_TIMEOUT = email_config.get('timeout', 30)

# 确保日志目录存在
logging_config = config_loader.get_logging_config()
log_dir = os.path.join(BASE_DIR, logging_config.get('dir', '../../logs'))
os.makedirs(log_dir, exist_ok=True)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': logging_config.get('format', '{levelname} {asctime} {module} {process:d} {thread:d} {message}'),
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'app.log'),
            'maxBytes': logging_config.get('max_bytes', 10) * 1024 * 1024,  # MB to bytes
            'backupCount': logging_config.get('backup_count', 10),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_dir, 'error.log'),
            'maxBytes': logging_config.get('max_bytes', 10) * 1024 * 1024,
            'backupCount': logging_config.get('backup_count', 10),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # 其他具体模块的 logger 配置
        'django': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.api_testing.views': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps.data_factory.tools.json_tools': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.data_factory.tools.encoding_tools': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.data_factory.tools': {
            'handlers': ['file', 'error_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['file', 'error_file', 'console'],
        'level': 'INFO',
        # 'propagate': True,
    },
}

# 指定simpleui默认的主题,指定一个文件名，相对路径就从simpleui的theme目录读取
SIMPLEUI_DEFAULT_THEME = 'admin.lte.css'
# 是否显示图标
SIMPLEUI_DEFAULT_ICON = True
# 是否关闭登录页粒子效果
SIMPLEUI_LOGIN_PARTICLES = True
# 后台管理首页，可以是url或者html文件
# SIMPLEUI_HOME_PAGE = 'https://www.baidu.com/'  # 后面可以扩展为大屏显示做统计
# 自定义首页标题
# SIMPLEUI_HOME_TITLE = 'Dashboard'
# # 自定义首页图标 首页图标,支持element-ui和fontawesome的图标，参考https://fontawesome.com/icons图标
# SIMPLEUI_HOME_ICON = 'fa fa-gauge'
# 设置simpleui 点击首页图标跳转的地址
SIMPLEUI_INDEX = 'http://localhost:3000'
# 自定义后台的Logo
SIMPLEUI_LOGO = 'https://static.djangoproject.com/img/favicon.6dbf28c0650e.ico'
# 是否显示首页信息
SIMPLEUI_HOME_INFO = False
# 是否显示快捷入口
SIMPLEUI_HOME_QUICK = True
# 是否显示最近动作
SIMPLEUI_HOME_ACTION = True
# 使用分析
SIMPLEUI_ANALYSIS = False
# 离线模式
SIMPLEUI_STATIC_OFFLINE = True
# True或None 默认显示加载遮罩层，指定为False 不显示遮罩层。默认显示
SIMPLEUI_LOADING = True
# 设置菜单icon，参考https://element.eleme.cn/#/zh-CN/component/icon
SIMPLEUI_ICON = {
    # 一级菜单项
    '测试执行管理': 'el-icon-s-tools',
    '用户管理': 'el-icon-user-solid',
    '令牌黑名单': 'el-icon-warning-outline',
    '接口测试': 'el-icon-s-platform',
    '智能助手': 'el-icon-chat-dot-round',
    '用例评审管理': 'el-icon-edit-outline',
    '认证令牌': 'el-icon-key',
    '认证和授权': 'el-icon-s-check',
    '需求分析': 'el-icon-notebook-2',

    # 二级菜单项
    '测试执行': 'el-icon-s-operation',
    '测试执行历史': 'el-icon-time',
    '测试执行用例': 'el-icon-document',
    '测试计划': 'el-icon-document-checked',
    '用户': 'el-icon-user',
    '用户配置': 'el-icon-setting',
    'Blacklisted Tokens': 'el-icon-warning-outline',
    'Outstanding Tokens': 'el-icon-s-custom',
    'API请求': 'el-icon-s-promotion',
    'API集合': 'el-icon-s-grid',
    'API项目': 'el-icon-s-custom',
    '任务执行日志': 'el-icon-s-data',
    '定时任务': 'el-icon-time',
    '测试套件': 'el-icon-suitcase',
    '环境变量': 'el-icon-school',
    '请求历史': 'el-icon-odometer',
    '智能助手会话': 'el-icon-chat-dot-round',
    '智能助手消息': 'el-icon-message',
    '测试用例评审': 'el-icon-check',
    '评审分配': 'el-icon-guide',
    '评审意见': 'el-icon-s-custom',
    '评审模板': 'el-icon-document',
    'Tokens': 'el-icon-key',
    '组': 'el-icon-s-custom',
    '业务需求': 'el-icon-document-checked',
    '分析任务': 'el-icon-stopwatch',
    '生成的测试用例': 'el-icon-document',
    '需求文档': 'el-icon-document',
}

# 开发环境，暂时禁用迁移历史检查
# SILENCED_SYSTEM_CHECKS = ['django.db.migrations.InconsistentMigrationHistory']

