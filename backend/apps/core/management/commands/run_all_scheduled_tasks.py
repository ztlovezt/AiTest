"""
已废弃的命令 - 请使用新的 Django-Q 调度器

此命令已被废弃，请使用以下方式替代：

1. 启动 Django-Q worker：
   python manage.py qcluster

新的调度器基于 Django-Q 实现，提供更好的可靠性和管理功能。

注意：旧版定时任务模型已被移除，请使用 scheduler 模块管理定时任务。
"""
import warnings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '[已废弃] 运行所有模块的定时任务调度器 - 请使用 python manage.py qcluster 替代'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='检查间隔（秒），默认60秒（已废弃）'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='只执行一次检查，不循环（已废弃）'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('警告: 此命令已废弃！'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write('')
        self.stdout.write('旧版定时任务模型已被移除：')
        self.stdout.write('  - api_testing.ScheduledTask')
        self.stdout.write('  - ui_automation.UiScheduledTask')
        self.stdout.write('  - app_automation.AppScheduledTask')
        self.stdout.write('')
        self.stdout.write('请使用新的 Django-Q 调度器替代：')
        self.stdout.write('')
        self.stdout.write('  启动 Django-Q worker：')
        self.stdout.write(self.style.SUCCESS('     python manage.py qcluster'))
        self.stdout.write('')
        self.stdout.write('新的调度器提供以下优势：')
        self.stdout.write('  - 更可靠的任务执行')
        self.stdout.write('  - 内置任务重试机制')
        self.stdout.write('  - 统一的任务管理界面')
        self.stdout.write('  - 支持多种调度类型（Cron、间隔、单次）')
        self.stdout.write('  - 完整的执行日志和统计')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 60))
        
        warnings.warn(
            'run_all_scheduled_tasks 命令已废弃，请使用 Django-Q 调度器 (python manage.py qcluster)',
            DeprecationWarning,
            stacklevel=2
        )
