"""
Core应用配置
在应用启动时加载配置文件
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = '核心模块'
    
    def ready(self):
        """应用启动时执行"""
        logger.info('Core应用启动，开始加载配置...')
        
        # 导入配置管理器
        from .management.commands.load_config import config_manager
        
        # 加载配置
        config_manager.load_config()
        
        # 记录配置信息
        server_config = config_manager.get_server_config()
        logger.info(f'服务器配置已加载: {server_config}')
        
        # 注册自定义 Django Q Admin（中文化）
        self._register_django_q_admin()
        
        logger.info('Core应用启动完成')
    
    def _register_django_q_admin(self):
        """注册自定义的 Django Q Admin"""
        from django.contrib import admin
        from django.utils.translation import gettext_lazy as _
        from django_q.models import Task, Schedule, Success, Failure
        from django_q.brokers import orm
        import json
        
        # 检查是否已注册，如果已注册则先取消
        if admin.site.is_registered(Task):
            admin.site.unregister(Task)
        if admin.site.is_registered(Schedule):
            admin.site.unregister(Schedule)
        if admin.site.is_registered(Success):
            admin.site.unregister(Success)
        if admin.site.is_registered(Failure):
            admin.site.unregister(Failure)
        
        # 尝试取消注册 OrmQ（如果存在）
        try:
            OrmQ = orm.OrmQ
            if admin.site.is_registered(OrmQ):
                admin.site.unregister(OrmQ)
        except Exception:
            OrmQ = None
        
        @admin.register(Task)
        class TaskAdmin(admin.ModelAdmin):
            list_display = ('col_id', 'col_name', 'col_func', 'col_group', 'col_started', 'col_stopped', 'col_success')
            list_filter = ('success', 'group')
            search_fields = ('name', 'func', 'group')
            readonly_fields = ('id', 'name', 'func', 'hook', 'args', 'kwargs', 
                               'result', 'group', 'cluster', 'started', 'stopped', 
                               'success', 'attempt_count')
            list_per_page = 20
            verbose_name = _('任务')
            verbose_name_plural = _('任务管理')
            
            @admin.display(description=_('ID'))
            def col_id(self, obj):
                return obj.id
            
            @admin.display(description=_('名称'))
            def col_name(self, obj):
                return obj.name
            
            @admin.display(description=_('函数'))
            def col_func(self, obj):
                return obj.func
            
            @admin.display(description=_('分组'))
            def col_group(self, obj):
                return obj.group or '-'
            
            @admin.display(description=_('开始时间'))
            def col_started(self, obj):
                return obj.started
            
            @admin.display(description=_('结束时间'))
            def col_stopped(self, obj):
                return obj.stopped
            
            @admin.display(description=_('状态'))
            def col_success(self, obj):
                return _('成功') if obj.success else _('失败')
            
            def has_add_permission(self, request):
                return False
            
            def has_change_permission(self, request, obj=None):
                return False
        
        @admin.register(Schedule)
        class ScheduleAdmin(admin.ModelAdmin):
            list_display = ('col_id', 'col_name', 'col_func', 'col_schedule_type', 'col_repeats', 'col_cluster', 'col_next_run', 'col_last_run', 'col_success_count')
            list_filter = ('schedule_type', 'cluster')
            search_fields = ('name', 'func', 'group')
            readonly_fields = ('id', 'name', 'func', 'hook', 'args', 'kwargs', 
                               'schedule_type', 'minutes', 'repeats', 'next_run', 
                               'cron', 'task', 'cluster')
            list_per_page = 20
            verbose_name = _('定时任务')
            verbose_name_plural = _('定时任务')
            
            @admin.display(description=_('ID'))
            def col_id(self, obj):
                return obj.id
            
            @admin.display(description=_('名称'))
            def col_name(self, obj):
                return obj.name
            
            @admin.display(description=_('函数'))
            def col_func(self, obj):
                return obj.func
            
            @admin.display(description=_('调度类型'))
            def col_schedule_type(self, obj):
                type_map = {
                    'O': _('单次'),
                    'H': _('每小时'),
                    'D': _('每天'),
                    'W': _('每周'),
                    'M': _('每月'),
                    'Q': _('每季度'),
                    'Y': _('每年'),
                    'C': _('Cron'),
                }
                return type_map.get(obj.schedule_type, obj.schedule_type or '-')
            
            @admin.display(description=_('重复次数'))
            def col_repeats(self, obj):
                return obj.repeats if obj.repeats != -1 else _('无限')
            
            @admin.display(description=_('集群'))
            def col_cluster(self, obj):
                return obj.cluster or '-'
            
            @admin.display(description=_('下次运行'))
            def col_next_run(self, obj):
                return obj.next_run or '-'
            
            @admin.display(description=_('上次运行'))
            def col_last_run(self, obj):
                if obj.task:
                    from django.urls import reverse
                    from django.utils.html import format_html
                    try:
                        url = reverse('admin:django_q_success_change', args=[obj.task])
                        return format_html('<a href="{}">{}</a>', url, obj.task)
                    except Exception:
                        return obj.task
                return '-'
            
            @admin.display(description=_('成功记录'))
            def col_success_count(self, obj):
                from django_q.models import Success
                count = Success.objects.filter(name=obj.name, func=obj.func).count()
                return count if count > 0 else '-'
        
        @admin.register(Success)
        class SuccessAdmin(admin.ModelAdmin):
            list_display = ('col_name', 'col_group', 'col_func', 'col_cluster', 'col_started', 'col_stopped', 'col_time_taken')
            list_filter = ('group', 'cluster')
            search_fields = ('name', 'func', 'group')
            readonly_fields = ('id', 'name', 'func', 'hook', 'args', 'kwargs',
                               'result', 'group', 'cluster', 'started', 'stopped', 
                               'success', 'attempt_count')
            list_per_page = 20
            verbose_name = _('成功记录')
            verbose_name_plural = _('成功记录')
            
            @admin.display(description=_('名称'))
            def col_name(self, obj):
                return obj.name
            
            @admin.display(description=_('分组'))
            def col_group(self, obj):
                return obj.group or '-'
            
            @admin.display(description=_('函数'))
            def col_func(self, obj):
                return obj.func
            
            @admin.display(description=_('集群'))
            def col_cluster(self, obj):
                return obj.cluster or '-'
            
            @admin.display(description=_('开始时间'))
            def col_started(self, obj):
                return obj.started
            
            @admin.display(description=_('结束时间'))
            def col_stopped(self, obj):
                return obj.stopped
            
            @admin.display(description=_('耗时'))
            def col_time_taken(self, obj):
                if obj.started and obj.stopped:
                    delta = obj.stopped - obj.started
                    total_seconds = delta.total_seconds()
                    if total_seconds < 1:
                        return f'{int(total_seconds * 1000)}ms'
                    elif total_seconds < 60:
                        return f'{total_seconds:.2f}s'
                    else:
                        minutes = int(total_seconds // 60)
                        seconds = total_seconds % 60
                        return f'{minutes}m {seconds:.1f}s'
                return '-'
            
            def has_add_permission(self, request):
                return False
            
            def has_change_permission(self, request, obj=None):
                return False
        
        @admin.register(Failure)
        class FailureAdmin(admin.ModelAdmin):
            list_display = ('col_name', 'col_group', 'col_func', 'col_cluster', 'col_started', 'col_stopped', 'col_short_result')
            list_filter = ('group', 'cluster')
            search_fields = ('name', 'func', 'group')
            readonly_fields = ('id', 'name', 'func', 'hook', 'args', 'kwargs',
                               'result', 'group', 'cluster', 'started', 'stopped', 
                               'success', 'attempt_count')
            list_per_page = 20
            verbose_name = _('失败记录')
            verbose_name_plural = _('失败记录')
            
            @admin.display(description=_('名称'))
            def col_name(self, obj):
                return obj.name
            
            @admin.display(description=_('分组'))
            def col_group(self, obj):
                return obj.group or '-'
            
            @admin.display(description=_('函数'))
            def col_func(self, obj):
                return obj.func
            
            @admin.display(description=_('集群'))
            def col_cluster(self, obj):
                return obj.cluster or '-'
            
            @admin.display(description=_('开始时间'))
            def col_started(self, obj):
                return obj.started
            
            @admin.display(description=_('结束时间'))
            def col_stopped(self, obj):
                return obj.stopped
            
            @admin.display(description=_('简短结果'))
            def col_short_result(self, obj):
                if obj.result:
                    result_str = str(obj.result)
                    if len(result_str) > 50:
                        return result_str[:50] + '...'
                    return result_str
                return '-'
            
            def has_add_permission(self, request):
                return False
            
            def has_change_permission(self, request, obj=None):
                return False
        
        # 注册 OrmQ Admin（队列任务）
        if OrmQ:
            @admin.register(OrmQ)
            class OrmQAdmin(admin.ModelAdmin):
                list_display = ('col_id', 'col_key', 'col_name', 'col_group', 'col_func', 'col_lock', 'col_task_id')
                list_filter = ('key',)
                search_fields = ('key', 'payload')
                readonly_fields = ('id', 'key', 'payload', 'lock')
                list_per_page = 20
                verbose_name = _('队列任务')
                verbose_name_plural = _('队列任务')
                
                def _parse_payload(self, obj):
                    """解析 payload 数据"""
                    try:
                        if obj.payload:
                            data = json.loads(obj.payload)
                            if isinstance(data, list) and len(data) > 0:
                                return data[0] if isinstance(data[0], dict) else {}
                            elif isinstance(data, dict):
                                return data
                    except (json.JSONDecodeError, TypeError):
                        pass
                    return {}
                
                @admin.display(description=_('ID'))
                def col_id(self, obj):
                    return obj.id
                
                @admin.display(description=_('键'))
                def col_key(self, obj):
                    return obj.key
                
                @admin.display(description=_('名称'))
                def col_name(self, obj):
                    data = self._parse_payload(obj)
                    return data.get('name', '-')
                
                @admin.display(description=_('分组'))
                def col_group(self, obj):
                    data = self._parse_payload(obj)
                    return data.get('group', '-')
                
                @admin.display(description=_('函数'))
                def col_func(self, obj):
                    data = self._parse_payload(obj)
                    return data.get('func', '-')
                
                @admin.display(description=_('锁'))
                def col_lock(self, obj):
                    return obj.lock or '-'
                
                @admin.display(description=_('任务ID'))
                def col_task_id(self, obj):
                    data = self._parse_payload(obj)
                    return data.get('task_id', data.get('id', '-'))
                
                def has_add_permission(self, request):
                    return False
                
                def has_change_permission(self, request, obj=None):
                    return False
