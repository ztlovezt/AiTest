"""
数据迁移命令
将现有定时任务迁移到新的统一调度器
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = '将现有定时任务迁移到统一调度器（基于Django-Q）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要迁移的任务，不实际执行迁移',
        )
        parser.add_argument(
            '--module',
            type=str,
            choices=['api', 'ui', 'app', 'all'],
            default='all',
            help='指定要迁移的模块（api/ui/app/all）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        module = options['module']

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('定时任务迁移工具'))
        self.stdout.write(self.style.SUCCESS(f'时间: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS(f'模式: {"模拟运行" if dry_run else "实际迁移"}'))
        self.stdout.write(self.style.SUCCESS(f'模块: {module}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        if dry_run:
            self._show_preview(module)
        else:
            self._do_migrate(module)

    def _show_preview(self, module):
        """显示预览"""
        from apps.api_testing.models import ScheduledTask as ApiScheduledTask
        from apps.ui_automation.models import UiScheduledTask
        from apps.app_automation.models import AppScheduledTask

        if module in ['api', 'all']:
            api_tasks = ApiScheduledTask.objects.all()
            self.stdout.write(f"\n[API测试模块] 共 {api_tasks.count()} 个定时任务:")
            for task in api_tasks:
                self.stdout.write(f"  - {task.name} ({task.get_task_type_display()}) - {task.get_status_display()}")

        if module in ['ui', 'all']:
            ui_tasks = UiScheduledTask.objects.all()
            self.stdout.write(f"\n[UI自动化模块] 共 {ui_tasks.count()} 个定时任务:")
            for task in ui_tasks:
                self.stdout.write(f"  - {task.name} ({task.get_task_type_display()}) - {task.get_status_display()}")

        if module in ['app', 'all']:
            app_tasks = AppScheduledTask.objects.all()
            self.stdout.write(f"\n[APP自动化模块] 共 {app_tasks.count()} 个定时任务:")
            for task in app_tasks:
                self.stdout.write(f"  - {task.name} ({task.get_task_type_display()}) - {task.get_status_display()}")

        self.stdout.write(self.style.WARNING("\n使用不带 --dry-run 参数执行实际迁移"))

    def _do_migrate(self, module):
        """执行迁移"""
        results = {'api': {'total': 0, 'migrated': 0, 'failed': 0},
                   'ui': {'total': 0, 'migrated': 0, 'failed': 0},
                   'app': {'total': 0, 'migrated': 0, 'failed': 0}}
        
        if module in ['api', 'all']:
            self._migrate_api_tasks(results)
        
        if module in ['ui', 'all']:
            self._migrate_ui_tasks(results)
        
        if module in ['app', 'all']:
            self._migrate_app_tasks(results)

        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('迁移完成'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        for mod, stats in results.items():
            self.stdout.write(
                f"[{mod.upper()}] 总计: {stats['total']}, "
                f"成功: {stats['migrated']}, 失败: {stats['failed']}"
            )
        
        self.stdout.write("\n提示: 请启动 Django-Q worker 来执行定时任务:")
        self.stdout.write("  python manage.py qcluster")

    def _migrate_api_tasks(self, results):
        """迁移API测试模块任务"""
        from apps.api_testing.models import ScheduledTask as ApiScheduledTask
        from apps.scheduler.models import create_scheduled_task
        
        for task in ApiScheduledTask.objects.all():
            results['api']['total'] += 1
            try:
                schedule_type = self._convert_trigger_type(task.trigger_type)
                task_type = 'API_TEST_SUITE' if task.task_type == 'TEST_SUITE' else 'API_REQUEST'
                
                create_scheduled_task(
                    name=task.name,
                    module='API',
                    task_type=task_type,
                    schedule_type=schedule_type,
                    target_id=task.test_suite_id or task.api_request_id,
                    project_id=task.test_suite.project_id if task.test_suite else None,
                    environment_id=task.environment_id,
                    cron=task.cron_expression,
                    minutes=task.interval_seconds // 60 if task.interval_seconds else None,
                    next_run=task.next_run_time,
                    created_by=task.created_by,
                    description=task.description,
                    notify_on_success=task.notify_on_success,
                    notify_on_failure=task.notify_on_failure,
                    notify_emails=task.notify_emails or [],
                )
                results['api']['migrated'] += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {task.name}"))
            except Exception as e:
                results['api']['failed'] += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {task.name}: {e}"))

    def _migrate_ui_tasks(self, results):
        """迁移UI自动化模块任务"""
        from apps.ui_automation.models import UiScheduledTask
        from apps.scheduler.models import create_scheduled_task
        
        for task in UiScheduledTask.objects.all():
            results['ui']['total'] += 1
            try:
                schedule_type = self._convert_trigger_type(task.trigger_type)
                task_type = 'UI_TEST_SUITE' if task.task_type == 'TEST_SUITE' else 'UI_TEST_CASE'
                
                task_config = {
                    'engine': task.engine,
                    'browser': task.browser,
                    'headless': task.headless,
                    'test_case_ids': task.test_cases or [],
                }
                
                create_scheduled_task(
                    name=task.name,
                    module='UI',
                    task_type=task_type,
                    schedule_type=schedule_type,
                    target_id=task.test_suite_id,
                    project_id=task.project_id,
                    task_config=task_config,
                    cron=task.cron_expression,
                    minutes=task.interval_seconds // 60 if task.interval_seconds else None,
                    next_run=task.next_run_time,
                    created_by=task.created_by,
                    description=task.description,
                    notify_on_success=task.notify_on_success,
                    notify_on_failure=task.notify_on_failure,
                    notify_emails=task.notify_emails or [],
                    webhook_url=getattr(task, 'webhook_url', ''),
                )
                results['ui']['migrated'] += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {task.name}"))
            except Exception as e:
                results['ui']['failed'] += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {task.name}: {e}"))

    def _migrate_app_tasks(self, results):
        """迁移APP自动化模块任务"""
        from apps.app_automation.models import AppScheduledTask
        from apps.scheduler.models import create_scheduled_task
        
        for task in AppScheduledTask.objects.all():
            results['app']['total'] += 1
            try:
                schedule_type = self._convert_trigger_type(task.trigger_type)
                task_type = 'APP_TEST_SUITE' if task.task_type == 'TEST_SUITE' else 'APP_TEST_CASE'
                
                task_config = {
                    'device_id': task.device_id,
                    'app_package_id': task.app_package_id,
                    'test_case_ids': task.test_cases or [],
                }
                
                create_scheduled_task(
                    name=task.name,
                    module='APP',
                    task_type=task_type,
                    schedule_type=schedule_type,
                    target_id=task.test_suite_id,
                    project_id=task.project_id,
                    task_config=task_config,
                    cron=task.cron_expression,
                    minutes=task.interval_seconds // 60 if task.interval_seconds else None,
                    next_run=task.next_run_time,
                    created_by=task.created_by,
                    description=task.description,
                    notify_on_success=task.notify_on_success,
                    notify_on_failure=task.notify_on_failure,
                    notify_emails=task.notify_emails or [],
                    webhook_url=task.webhook_url or '',
                )
                results['app']['migrated'] += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ {task.name}"))
            except Exception as e:
                results['app']['failed'] += 1
                self.stdout.write(self.style.ERROR(f"  ✗ {task.name}: {e}"))

    def _convert_trigger_type(self, trigger_type):
        """转换触发类型到Django-Q类型"""
        type_map = {
            'CRON': 'C',
            'INTERVAL': 'I',
            'ONCE': 'O',
        }
        return type_map.get(trigger_type, 'O')
