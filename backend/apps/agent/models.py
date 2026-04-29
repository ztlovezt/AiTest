import hashlib
import uuid

from django.conf import settings
from django.db import models


class AgentModelConfig(models.Model):
    PROVIDER_CHOICES = [
        ("openai_compatible", "OpenAI Compatible"),
        ("custom", "自定义"),
    ]

    name = models.CharField(max_length=120, verbose_name="配置名称")
    provider = models.CharField(
        max_length=32, choices=PROVIDER_CHOICES, default="openai_compatible", verbose_name="提供商"
    )
    api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="API Key")
    base_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="Base URL")
    model_name = models.CharField(max_length=120, blank=True, null=True, verbose_name="模型名称")
    max_tokens = models.IntegerField(default=2048, verbose_name="最大Token数")
    temperature = models.FloatField(default=0.3, verbose_name="温度")
    top_p = models.FloatField(default=0.9, verbose_name="Top P")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建者"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "agent_model_configs"
        verbose_name = "Agent模型配置"
        verbose_name_plural = "Agent模型配置"
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if self.is_active:
            AgentModelConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_config(cls):
        return cls.objects.filter(is_active=True).first()


class AgentSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="agent_sessions")
    session_id = models.CharField(max_length=64, unique=True, default="", verbose_name="会话ID")
    title = models.CharField(max_length=500, blank=True, verbose_name="会话标题")
    preset_code = models.CharField(max_length=64, default="general_qa", verbose_name="预设")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "agent_sessions"
        verbose_name = "Agent会话"
        verbose_name_plural = "Agent会话"
        ordering = ["-updated_at"]

    def save(self, *args, **kwargs):
        if not self.session_id:
            self.session_id = f"sess_{uuid.uuid4().hex}"
        super().save(*args, **kwargs)


class AgentMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "用户"),
        ("assistant", "助手"),
        ("system", "系统"),
        ("tool", "工具"),
    ]

    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_messages"
        verbose_name = "Agent消息"
        verbose_name_plural = "Agent消息"
        ordering = ["created_at"]


class AgentToolCall(models.Model):
    STATUS_CHOICES = [
        ("pending", "待执行"),
        ("running", "执行中"),
        ("success", "成功"),
        ("failed", "失败"),
    ]

    session = models.ForeignKey(AgentSession, on_delete=models.CASCADE, related_name="tool_calls")
    assistant_message = models.ForeignKey(
        AgentMessage, on_delete=models.CASCADE, related_name="tool_calls", null=True, blank=True
    )
    preset_code = models.CharField(max_length=64, default="general_qa")
    tool_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    arguments = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_tool_calls"
        verbose_name = "Agent工具调用"
        verbose_name_plural = "Agent工具调用"
        ordering = ["-created_at"]


class AgentBuiltinDocument(models.Model):
    source_path = models.CharField(max_length=500, unique=True)
    title = models.CharField(max_length=255)
    content = models.TextField()
    checksum = models.CharField(max_length=64, default="", db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "agent_builtin_documents"
        verbose_name = "Agent内置文档"
        verbose_name_plural = "Agent内置文档"

    @staticmethod
    def content_checksum(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AgentBuiltinChunk(models.Model):
    document = models.ForeignKey(AgentBuiltinDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField(default=0)
    content = models.TextField()
    token_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "agent_builtin_chunks"
        verbose_name = "Agent内置文档分块"
        verbose_name_plural = "Agent内置文档分块"
        ordering = ["document_id", "chunk_index"]
        unique_together = ["document", "chunk_index"]
