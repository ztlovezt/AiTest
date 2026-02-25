"""
自定义运行服务器命令
自动使用 config.yaml 中配置的端口
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.servers.basehttp import WSGIServer


class Command(BaseCommand):
    help = '使用配置文件中的端口启动开发服务器'

    def add_arguments(self, parser):
        parser.add_argument(
            'addrport',
            nargs='?',
            default=None,
            help='Optional port number, or ipaddr:port'
        )
        parser.add_argument(
            '--ipv6',
            '-6',
            action='store_true',
            dest='use_ipv6',
            help='Tells Django to use an IPv6 address.',
        )
        parser.add_argument(
            '--nothreading',
            action='store_true',
            dest='nothreading',
            help='Tells Django to NOT use threading.',
        )
        parser.add_argument(
            '--noreload',
            action='store_true',
            dest='noreload',
            help='Tells Django to NOT use the auto-reloader.',
        )

    def handle(self, *args, **options):
        import django
        from django.core.management import call_command
        
        # 获取配置的端口
        backend_port = getattr(settings, 'BACKEND_PORT', 8000)
        backend_host = '127.0.0.1'
        
        # 如果没有指定端口，使用配置文件中的端口
        addrport = options.get('addrport')
        if addrport is None:
            addrport = f'{backend_host}:{backend_port}'
            self.stdout.write(f'使用配置文件中的端口: {backend_port}\n')
        
        # 调用原始的runserver命令
        call_command('runserver', addrport, **options)