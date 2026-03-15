# -*- coding: utf-8 -*-
# -----------------------------
# @Author    : 影子
# @Time      : 2026/3/7 00:21
# @Software  : PyCharm
# @FileName  : aggregate_performance_stats.py
# -----------------------------
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from apps.core.models import RequestPerformanceLog, PerformanceStatistics


class Command(BaseCommand):
    """
    聚合性能统计数据
    """
    help = '聚合性能统计数据'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='指定日期 (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--today',
            action='store_true',
            help='统计今天的数据',
        )
        parser.add_argument(
            '--yesterday',
            action='store_true',
            help='统计昨天的数据（默认）',
        )
    
    def handle(self, *args, **options):
        if options['today']:
            target_date = timezone.now().date()
        elif options['date']:
            target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            target_date = (timezone.now() - timedelta(days=1)).date()
        
        self.stdout.write(f'正在聚合 {target_date} 的性能统计数据...')
        
        start_time = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        if options['today']:
            end_time = timezone.now()
        else:
            end_time = start_time + timedelta(days=1)
        
        logs = RequestPerformanceLog.objects.filter(
            created_at__gte=start_time,
            created_at__lte=end_time
        )
        
        total_requests = logs.count()
        
        if total_requests == 0:
            self.stdout.write(self.style.WARNING(f'{target_date} 没有请求记录'))
            return
        
        avg_response_time = sum(log.response_time for log in logs) / total_requests
        max_response_time = max(log.response_time for log in logs)
        min_response_time = min(log.response_time for log in logs)
        error_count = logs.filter(status_code__gte=400).count()
        slow_requests = logs.filter(response_time__gt=1000).count()
        
        stats, created = PerformanceStatistics.objects.update_or_create(
            date=target_date,
            defaults={
                'total_requests': total_requests,
                'avg_response_time': avg_response_time,
                'max_response_time': max_response_time,
                'min_response_time': min_response_time,
                'error_count': error_count,
                'slow_requests': slow_requests,
            }
        )
        
        action = '创建' if created else '更新'
        self.stdout.write(self.style.SUCCESS(
            f'{action}性能统计: {target_date} - 总请求: {total_requests}, '
            f'平均响应时间: {avg_response_time:.2f}ms, '
            f'错误数: {error_count}, 慢请求: {slow_requests}'
        ))
