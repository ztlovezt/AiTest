"""统一邮件发送服务"""
from backend.utils.modern_email import ModernEmailSender
from backend.log_config import get_logger
from django.conf import settings
from typing import List, Optional, Dict, Any

logger = get_logger('email')


class EmailService:
    """统一邮件发送服务"""
    
    def __init__(self):
        self.email_sender = ModernEmailSender()
        self.default_from_email = settings.DEFAULT_FROM_EMAIL
    
    def send_notification_email(
        self,
        subject: str,
        message: str,
        recipients: List[str],
        html_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """发送通知邮件
        
        Args:
            subject: 邮件主题
            message: 邮件正文（纯文本）
            recipients: 收件人列表
            html_content: HTML内容（可选）
            attachments: 附件列表（可选）
            cc: 抄送列表（可选）
            bcc: 密送列表（可选）
        
        Returns:
            bool: 是否发送成功
        """
        try:
            logger.info(f"准备发送邮件: 主题='{subject}', 收件人={recipients}")
            
            if not recipients:
                logger.warning("收件人列表为空，跳过邮件发送")
                return False
            
            if html_content:
                # 发送HTML邮件
                result = self.email_sender.send_html_email(
                    subject=subject,
                    text_body=message,
                    html_body=html_content,
                    to=recipients,
                    cc=cc,
                    bcc=bcc,
                    attachments=attachments
                )
            else:
                # 发送纯文本邮件
                result = self.email_sender.send_simple_email(
                    subject=subject,
                    body=message,
                    to=recipients,
                    cc=cc,
                    bcc=bcc
                )
            
            if result:
                logger.info(f"邮件发送成功: 主题='{subject}'")
            else:
                logger.error(f"邮件发送失败: 主题='{subject}'")
            
            return result
            
        except Exception as e:
            logger.error(f"邮件发送异常: 主题='{subject}', 错误={str(e)}", exc_info=True)
            return False
    
    def send_task_notification(
        self,
        task_name: str,
        task_type: str,
        status: str,
        recipients: List[str],
        details: str = "",
        execution_time: Optional[str] = None,
        result: Optional[str] = None
    ) -> bool:
        """发送任务通知邮件
        
        Args:
            task_name: 任务名称
            task_type: 任务类型
            status: 任务状态（success/failed）
            recipients: 收件人列表
            details: 详细信息
            execution_time: 执行时间
            result: 执行结果
        
        Returns:
            bool: 是否发送成功
        """
        status_text = "成功" if status == 'success' else "失败"
        subject = f"[TestHub] {task_type}任务执行{status_text}: {task_name}"
        
        message = f"""
任务名称: {task_name}
任务类型: {task_type}
执行状态: {status_text}
"""
        
        if execution_time:
            message += f"执行时间: {execution_time}\n"
        if details:
            message += f"详细信息: {details}\n"
        if result:
            message += f"执行结果: {result}\n"
        
        message += f"\n此邮件由系统自动发送，请勿回复。"
        
        # 先生成HTML变量
        execution_time_html = f"<p><strong>执行时间:</strong> {execution_time}</p>" if execution_time else ""
        details_html = f"<p><strong>详细信息:</strong> {details}</p>" if details else ""
        result_html = f"<p><strong>执行结果:</strong> {result}</p>" if result else ""
        
        # 生成HTML内容（使用普通字符串，避免f-string和format冲突）
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 15px; border-bottom: 1px solid #e9ecef; }}
        .content {{ padding: 20px; }}
        .footer {{ margin-top: 20px; padding-top: 15px; border-top: 1px solid #e9ecef; font-size: 12px; color: #6c757d; }}
        .status-success {{ color: #28a745; font-weight: bold; }}
        .status-failed {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>TestHub 任务通知</h2>
        </div>
        <div class="content">
            <p><strong>任务名称:</strong> {task_name}</p>
            <p><strong>任务类型:</strong> {task_type}</p>
            <p><strong>执行状态:</strong> <span class="status-{status}">{status_text}</span></p>
            {execution_time_html}
            {details_html}
            {result_html}
        </div>
        <div class="footer">
            <p>此邮件由系统自动发送，请勿回复。</p>
        </div>
    </div>
</body>
</html>
"""
        
        html_content = html_content.format(
            task_name=task_name,
            task_type=task_type,
            status=status,
            status_text=status_text,
            execution_time_html=execution_time_html,
            details_html=details_html,
            result_html=result_html
        )
        
        return self.send_notification_email(
            subject=subject,
            message=message,
            html_content=html_content,
            recipients=recipients
        )
    
    def send_bulk_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量发送邮件
        
        Args:
            emails: 邮件列表，每个邮件包含subject, message, to等字段
        
        Returns:
            Dict: 发送结果统计
        """
        total = len(emails)
        success_count = 0
        failed_count = 0
        failed_emails = []
        
        for email_data in emails:
            try:
                subject = email_data.get('subject', '')
                message = email_data.get('message', '')
                to = email_data.get('to', [])
                html_content = email_data.get('html_content')
                
                if self.send_notification_email(
                    subject=subject,
                    message=message,
                    recipients=to,
                    html_content=html_content
                ):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_emails.append({
                        'subject': subject,
                        'to': to
                    })
            except Exception as e:
                logger.error(f"批量发送邮件异常: {str(e)}", exc_info=True)
                failed_count += 1
                failed_emails.append({
                    'subject': email_data.get('subject', ''),
                    'to': email_data.get('to', [])
                })
        
        result = {
            'total': total,
            'success': success_count,
            'failed': failed_count,
            'failed_emails': failed_emails
        }
        
        logger.info(f"批量邮件发送完成: {result}")
        return result


# 全局邮件服务实例
email_service = EmailService()
