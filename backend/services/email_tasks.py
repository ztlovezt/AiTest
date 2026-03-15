"""邮件异步任务"""
from django_q.tasks import async_task
from .email_service import email_service


def _send_task_notification_wrapper(task_name, task_type, status, recipients, details="", execution_time=None, result=None):
    """发送任务通知邮件的包装函数"""
    return email_service.send_task_notification(
        task_name=task_name,
        task_type=task_type,
        status=status,
        recipients=recipients,
        details=details,
        execution_time=execution_time,
        result=result
    )


def send_task_notification_task(task_name, task_type, status, recipients, details="", execution_time=None, result=None):
    """异步发送任务通知邮件
    
    Args:
        task_name: 任务名称
        task_type: 任务类型
        status: 任务状态（success/failed）
        recipients: 收件人列表
        details: 详细信息
        execution_time: 执行时间
        result: 执行结果
    
    Returns:
        str: 任务ID
    """
    # 从task_type中提取模块名称作为分组
    group = '通知任务'
    if task_type:
        if 'API' in task_type:
            group = 'API测试'
        elif 'UI' in task_type:
            group = 'UI测试'
        elif 'APP' in task_type:
            group = 'APP测试'
    
    return async_task(
        _send_task_notification_wrapper,
        task_name,
        task_type,
        status,
        recipients,
        details,
        execution_time,
        result,
        group=group
    )


def _send_notification_email_wrapper(subject, message, recipients, html_content=None, attachments=None, cc=None, bcc=None):
    """发送通知邮件的包装函数"""
    return email_service.send_notification_email(
        subject=subject,
        message=message,
        recipients=recipients,
        html_content=html_content,
        attachments=attachments,
        cc=cc,
        bcc=bcc
    )


def send_notification_email_task(subject, message, recipients, html_content=None, attachments=None, cc=None, bcc=None):
    """异步发送通知邮件
    
    Args:
        subject: 邮件主题
        message: 邮件正文（纯文本）
        recipients: 收件人列表
        html_content: HTML内容（可选）
        attachments: 附件列表（可选）
        cc: 抄送列表（可选）
        bcc: 密送列表（可选）
    
    Returns:
        str: 任务ID
    """
    return async_task(
        _send_notification_email_wrapper,
        subject,
        message,
        recipients,
        html_content,
        attachments,
        cc,
        bcc
    )


def _send_bulk_emails_wrapper(emails):
    """批量发送邮件的包装函数"""
    return email_service.send_bulk_emails(emails)


def send_bulk_emails_task(emails):
    """异步批量发送邮件
    
    Args:
        emails: 邮件列表，每个邮件包含subject, message, to等字段
    
    Returns:
        str: 任务ID
    """
    return async_task(_send_bulk_emails_wrapper, emails)
