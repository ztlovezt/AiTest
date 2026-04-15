from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
import ssl
import smtplib
import base64
from backend.log_config import get_logger

logger = get_logger(__name__)


class CustomEmailBackend(EmailBackend):
    def open(self):
        """打开SMTP连接，使用自定义SSL上下文"""
        if self.connection:
            return False

        ssl_context = ssl._create_unverified_context()

        try:
            if self.use_ssl:
                self.connection = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    context=ssl_context,
                    timeout=self.timeout
                )
            else:
                self.connection = smtplib.SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )
                if self.use_tls:
                    self.connection.starttls(context=ssl_context)

            if self.username and self.password:
                self._login_utf8()
            return True
        except smtplib.SMTPAuthenticationError as e:
            error_msg = (
                f"邮件服务认证失败：用户名或密码（授权码）错误。\n"
                f"请检查邮箱服务是否正常可用，确认以下配置：\n"
                f"1. SMTP 服务器地址：{self.host}\n"
                f"2. SMTP 端口：{self.port}\n"
                f"3. 邮箱账号：{self.username}\n"
                f"4. 授权码是否有效（QQ邮箱需在设置中重新生成授权码）"
            )
            logger.error(f"❌ {error_msg}")
            if not self.fail_silently:
                raise smtplib.SMTPAuthenticationError(e.smtp_code, error_msg.encode('utf-8'))
        except smtplib.SMTPServerDisconnected as e:
            error_msg = (
                f"邮件服务连接中断：{str(e)}\n"
                f"请检查邮箱服务是否正常可用，可能的原因：\n"
                f"1. SMTP 服务器不可达或网络问题\n"
                f"2. 邮箱账号被限制或封禁\n"
                f"3. 授权码已过期，请重新生成\n"
                f"4. 防火墙阻止了 {self.port} 端口连接\n"
                f"5. 请把 SSL 或 TLS 配置设置为true尝试"
            )
            logger.error(f"❌ {error_msg}")
            if not self.fail_silently:
                raise smtplib.SMTPServerDisconnected(error_msg)
        except smtplib.SMTPConnectError as e:
            error_msg = (
                f"邮件服务连接失败：{str(e)}\n"
                f"请检查邮箱服务是否正常可用，确认 SMTP 服务器地址和端口是否正确"
            )
            logger.error(f"❌ {error_msg}")
            if not self.fail_silently:
                raise smtplib.SMTPConnectError(e.smtp_code, error_msg.encode('utf-8'))
        except Exception as e:
            error_msg = (
                f"邮件服务异常：{type(e).__name__}: {str(e)}\n"
                f"请检查邮箱服务是否正常可用，或联系管理员检查邮件配置"
            )
            logger.error(f"❌ {error_msg}")
            if not self.fail_silently:
                raise

    def _login_utf8(self):
        """支持UTF-8编码的用户名和密码登录"""
        try:
            self.connection.ehlo_or_helo_if_needed()

            auth_methods = self.connection.esmtp_features.get('AUTH', '').split()

            if 'LOGIN' in auth_methods:
                self.connection.docmd('AUTH LOGIN')
                self.connection.docmd(base64.b64encode(self.username.encode('utf-8')).decode('ascii'))
                self.connection.docmd(base64.b64encode(self.password.encode('utf-8')).decode('ascii'))
            else:
                auth_string = f'\x00{self.username}\x00{self.password}'
                self.connection.docmd('AUTH PLAIN', base64.b64encode(auth_string.encode('utf-8')).decode('ascii'))
        except smtplib.SMTPAuthenticationError as e:
            raise smtplib.SMTPAuthenticationError(e.smtp_code, e.smtp_error)
