# -*- coding: utf-8 -*-
"""
第三方库模型中文 verbose_name 补丁
在 Django 启动时动态修改第三方库模型的 verbose_name
"""


def patch_third_party_models():
    """
    为第三方库模型添加中文 verbose_name
    """
    from django.utils.translation import gettext_lazy as _
    
    try:
        from rest_framework.authtoken.models import Token
        Token._meta.verbose_name = _('令牌')
        Token._meta.verbose_name_plural = _('令牌管理')
        Token._meta.get_field('key').verbose_name = _('令牌密钥')
        Token._meta.get_field('user').verbose_name = _('用户')
        Token._meta.get_field('created').verbose_name = _('创建时间')
    except Exception:
        pass
    
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
        OutstandingToken._meta.verbose_name = _('有效令牌')
        OutstandingToken._meta.verbose_name_plural = _('有效令牌管理')
        OutstandingToken._meta.get_field('jti').verbose_name = _('JWT ID')
        OutstandingToken._meta.get_field('token').verbose_name = _('令牌')
        OutstandingToken._meta.get_field('created_at').verbose_name = _('创建时间')
        OutstandingToken._meta.get_field('expires_at').verbose_name = _('过期时间')
        OutstandingToken._meta.get_field('user').verbose_name = _('用户')
    except Exception:
        pass
    
    try:
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        BlacklistedToken._meta.verbose_name = _('黑名单令牌')
        BlacklistedToken._meta.verbose_name_plural = _('黑名单令牌管理')
        BlacklistedToken._meta.get_field('token').verbose_name = _('令牌')
        BlacklistedToken._meta.get_field('blacklisted_at').verbose_name = _('加入黑名单时间')
    except Exception:
        pass
    
    try:
        from django_q.models import Task
        Task._meta.verbose_name = _('异步任务')
        Task._meta.verbose_name_plural = _('异步任务管理')
        Task._meta.get_field('name').verbose_name = _('任务名称')
        Task._meta.get_field('func').verbose_name = _('执行函数')
        Task._meta.get_field('hook').verbose_name = _('回调函数')
        Task._meta.get_field('args').verbose_name = _('位置参数')
        Task._meta.get_field('kwargs').verbose_name = _('关键字参数')
        Task._meta.get_field('result').verbose_name = _('执行结果')
        Task._meta.get_field('group').verbose_name = _('任务组')
        Task._meta.get_field('started').verbose_name = _('开始时间')
        Task._meta.get_field('stopped').verbose_name = _('结束时间')
        Task._meta.get_field('success').verbose_name = _('是否成功')
        Task._meta.get_field('attempt_count').verbose_name = _('重试次数')
    except Exception:
        pass
    
    try:
        from django_q.models import Schedule
        Schedule._meta.verbose_name = _('定时任务')
        Schedule._meta.verbose_name_plural = _('定时任务管理')
        Schedule._meta.get_field('func').verbose_name = _('执行函数')
        Schedule._meta.get_field('hook').verbose_name = _('回调函数')
        Schedule._meta.get_field('args').verbose_name = _('位置参数')
        Schedule._meta.get_field('kwargs').verbose_name = _('关键字参数')
        Schedule._meta.get_field('schedule_type').verbose_name = _('调度类型')
        Schedule._meta.get_field('repeats').verbose_name = _('重复次数')
        Schedule._meta.get_field('next_run').verbose_name = _('下次执行时间')
        Schedule._meta.get_field('task').verbose_name = _('任务ID')
        Schedule._meta.get_field('name').verbose_name = _('任务名称')
        Schedule._meta.get_field('minutes').verbose_name = _('分钟间隔')
        Schedule._meta.get_field('cron').verbose_name = _('Cron表达式')
        Schedule._meta.get_field('cluster').verbose_name = _('集群名称')
        Schedule._meta.get_field('intended_date_kwarg').verbose_name = _('预期日期参数名')
    except Exception:
        pass
    
    try:
        from django_q.models import Success
        Success._meta.verbose_name = _('成功任务')
        Success._meta.verbose_name_plural = _('成功任务记录')
    except Exception:
        pass
    
    try:
        from django_q.models import Failure
        Failure._meta.verbose_name = _('失败任务')
        Failure._meta.verbose_name_plural = _('失败任务记录')
    except Exception:
        pass
    
    try:
        from django_q.brokers import orm
        OrmQ = orm.OrmQ
        OrmQ._meta.verbose_name = _('任务队列')
        OrmQ._meta.verbose_name_plural = _('任务队列管理')
        OrmQ._meta.get_field('key').verbose_name = _('队列键')
        OrmQ._meta.get_field('payload').verbose_name = _('任务数据')
        OrmQ._meta.get_field('lock').verbose_name = _('锁')
    except Exception:
        pass


def patch_django_builtin_models():
    """
    为 Django 内置模型添加中文 verbose_name
    """
    from django.utils.translation import gettext_lazy as _
    
    try:
        from django.contrib.auth.models import User
        User._meta.verbose_name = _('用户')
        User._meta.verbose_name_plural = _('用户管理')
        User._meta.get_field('password').verbose_name = _('密码')
        User._meta.get_field('last_login').verbose_name = _('最后登录时间')
        User._meta.get_field('is_superuser').verbose_name = _('超级管理员')
        User._meta.get_field('username').verbose_name = _('用户名')
        User._meta.get_field('first_name').verbose_name = _('名')
        User._meta.get_field('last_name').verbose_name = _('姓')
        User._meta.get_field('email').verbose_name = _('邮箱')
        User._meta.get_field('is_staff').verbose_name = _('职员')
        User._meta.get_field('is_active').verbose_name = _('激活')
        User._meta.get_field('date_joined').verbose_name = _('注册时间')
    except Exception:
        pass
    
    try:
        from django.contrib.auth.models import Group
        Group._meta.verbose_name = _('用户组')
        Group._meta.verbose_name_plural = _('用户组管理')
        Group._meta.get_field('name').verbose_name = _('组名')
    except Exception:
        pass
    
    try:
        from django.contrib.auth.models import Permission
        Permission._meta.verbose_name = _('权限')
        Permission._meta.verbose_name_plural = _('权限管理')
        Permission._meta.get_field('name').verbose_name = _('权限名称')
        Permission._meta.get_field('content_type').verbose_name = _('内容类型')
        Permission._meta.get_field('codename').verbose_name = _('权限代码')
    except Exception:
        pass
    
    try:
        from django.contrib.contenttypes.models import ContentType
        ContentType._meta.verbose_name = _('内容类型')
        ContentType._meta.verbose_name_plural = _('内容类型管理')
        ContentType._meta.get_field('app_label').verbose_name = _('应用标签')
        ContentType._meta.get_field('model').verbose_name = _('模型名称')
    except Exception:
        pass
    
    try:
        from django.contrib.admin.models import LogEntry
        LogEntry._meta.verbose_name = _('操作日志')
        LogEntry._meta.verbose_name_plural = _('操作日志管理')
        LogEntry._meta.get_field('action_time').verbose_name = _('操作时间')
        LogEntry._meta.get_field('user').verbose_name = _('操作用户')
        LogEntry._meta.get_field('content_type').verbose_name = _('内容类型')
        LogEntry._meta.get_field('object_id').verbose_name = _('对象ID')
        LogEntry._meta.get_field('object_repr').verbose_name = _('对象表示')
        LogEntry._meta.get_field('action_flag').verbose_name = _('操作类型')
        LogEntry._meta.get_field('change_message').verbose_name = _('变更信息')
    except Exception:
        pass
    
    try:
        from django.contrib.sessions.models import Session
        Session._meta.verbose_name = _('会话')
        Session._meta.verbose_name_plural = _('会话管理')
        Session._meta.get_field('session_key').verbose_name = _('会话密钥')
        Session._meta.get_field('session_data').verbose_name = _('会话数据')
        Session._meta.get_field('expire_date').verbose_name = _('过期时间')
    except Exception:
        pass
