from django.contrib import admin

from apps.core.admin_mixins import StandardAdminMixin

from .models import (
    AgentBuiltinChunk,
    AgentBuiltinDocument,
    AgentMessage,
    AgentModelConfig,
    AgentSession,
    AgentToolCall,
)


@admin.register(AgentModelConfig)
class AgentModelConfigAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["name", "provider", "model_name", "is_active", "updated_at"]
    search_fields = ["name", "provider", "model_name"]
    list_filter = ["provider", "is_active"]


@admin.register(AgentSession)
class AgentSessionAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["session_id", "user", "title", "preset_code", "updated_at"]
    search_fields = ["session_id", "title", "user__username"]
    list_filter = ["preset_code", "updated_at"]


@admin.register(AgentMessage)
class AgentMessageAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["session", "role", "created_at"]
    search_fields = ["session__session_id", "content"]
    list_filter = ["role", "created_at"]


@admin.register(AgentToolCall)
class AgentToolCallAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["tool_name", "status", "session", "created_at", "finished_at"]
    search_fields = ["tool_name", "session__session_id", "error_message"]
    list_filter = ["status", "preset_code"]


@admin.register(AgentBuiltinDocument)
class AgentBuiltinDocumentAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["title", "source_path", "is_active", "updated_at"]
    search_fields = ["title", "source_path"]
    list_filter = ["is_active", "updated_at"]


@admin.register(AgentBuiltinChunk)
class AgentBuiltinChunkAdmin(StandardAdminMixin, admin.ModelAdmin):
    list_display = ["document", "chunk_index", "token_count", "created_at"]
    search_fields = ["document__title", "document__source_path", "content"]
