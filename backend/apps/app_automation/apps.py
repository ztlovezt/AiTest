# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _bootstrap_app_system_schedules(**kwargs):
    """
    在迁移完成后补齐 APP 自动化系统任务。
    """
    from .system_schedules import ensure_app_system_schedules_safely

    ensure_app_system_schedules_safely()


class AppAutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.app_automation"
    verbose_name = "APP自动化测试"

    def ready(self):
        try:
            import apps.app_automation.tasks  # noqa: F401
        except ImportError:
            pass

        post_migrate.connect(
            _bootstrap_app_system_schedules,
            sender=self,
            dispatch_uid="app_automation_bootstrap_system_schedules",
        )
