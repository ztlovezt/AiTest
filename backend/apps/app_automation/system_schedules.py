# -*- coding: utf-8 -*-
"""
APP 自动化系统级定时任务初始化。

这里维护的是平台运行所需的基础任务，而不是用户在页面上创建的业务任务。
"""

from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone
from django_q.models import Schedule


APP_SYSTEM_SCHEDULES = [
    {
        "name": "APP设备状态检查",
        "func": "apps.app_automation.tasks.check_device_status_task",
        "schedule_type": Schedule.MINUTES,
        "minutes": 10,
        "repeats": -1,
    },
    {
        "name": "APP设备锁定释放检查",
        "func": "apps.app_automation.tasks.check_and_release_expired_devices",
        "schedule_type": Schedule.MINUTES,
        "minutes": 1,
        "repeats": -1,
    },
]


def ensure_app_system_schedules():
    """
    幂等创建或更新 APP 自动化基础系统任务。

    返回:
        dict: {"created": int, "updated": int}
    """
    created_count = 0
    updated_count = 0

    for item in APP_SYSTEM_SCHEDULES:
        schedule, created = Schedule.objects.update_or_create(
            name=item["name"],
            defaults={
                "func": item["func"],
                "schedule_type": item["schedule_type"],
                "minutes": item.get("minutes"),
                "cron": item.get("cron"),
                "repeats": item.get("repeats", -1),
                "next_run": timezone.now(),
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    return {
        "created": created_count,
        "updated": updated_count,
    }


def ensure_app_system_schedules_safely():
    """
    安全包装，避免数据库尚未准备好时影响启动。
    """
    try:
        return ensure_app_system_schedules()
    except (OperationalError, ProgrammingError):
        return None
