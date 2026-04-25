from rest_framework import serializers

from .models import AgentMessage, AgentSession, AgentToolCall


class AgentToolCallSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentToolCall
        fields = [
            "id",
            "preset_code",
            "tool_name",
            "status",
            "arguments",
            "result",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
        ]


class AgentMessageSerializer(serializers.ModelSerializer):
    tool_calls = serializers.SerializerMethodField()

    class Meta:
        model = AgentMessage
        fields = ["id", "role", "content", "metadata", "created_at", "tool_calls"]

    def get_tool_calls(self, obj):
        if obj.role != "assistant":
            return []
        queryset = AgentToolCall.objects.filter(assistant_message=obj).order_by("created_at")
        return AgentToolCallSerializer(queryset, many=True).data


class AgentSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentSession
        fields = ["id", "session_id", "title", "preset_code", "created_at", "updated_at"]
