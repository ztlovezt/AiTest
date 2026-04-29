# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule

from apps.app_automation.system_schedules import ensure_app_system_schedules


class Command(BaseCommand):
    help = "初始化系统级定时任务"

    def handle(self, *args, **options):
        self.stdout.write("正在初始化系统级定时任务...")

        base_tasks = [
            {
                "name": "每日性能统计聚合",
                "func": "apps.core.tasks.aggregate_daily_performance_stats",
                "schedule_type": Schedule.DAILY,
                "minutes": 0,
                "repeats": -1,
            },
            {
                "name": "实时性能统计聚合",
                "func": "apps.core.tasks.aggregate_current_day_stats",
                "schedule_type": Schedule.MINUTES,
                "minutes": 30,
                "repeats": -1,
            },
        ]

        for item in base_tasks:
            schedule, created = Schedule.objects.update_or_create(
                name=item["name"],
                defaults={
                    "func": item["func"],
                    "schedule_type": item["schedule_type"],
                    "minutes": item.get("minutes"),
                    "repeats": item.get("repeats", -1),
                    "next_run": timezone.now(),
                },
            )
            action = "创建" if created else "更新"
            self.stdout.write(self.style.SUCCESS(f"{action}定时任务: {schedule.name}"))

        app_result = ensure_app_system_schedules()
        self.stdout.write(
            self.style.SUCCESS(
                f"APP 系统任务检查完成: 新建 {app_result['created']} 个, 更新 {app_result['updated']} 个"
            )
        )

        self.stdout.write(self.style.SUCCESS("系统级定时任务初始化完成"))
        self.stdout.write("")
        self.stdout.write("请确保已启动 Django Q 集群:")
        self.stdout.write("  python manage.py qcluster")
