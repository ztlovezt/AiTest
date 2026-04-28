from rest_framework import serializers

from .models import AgentMessage, AgentModelConfig, AgentSession, AgentToolCall


class AgentToolCallSerializer(serializers.ModelSerializer):
    duration_ms = serializers.SerializerMethodField()

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
            "duration_ms",
        ]

    def get_duration_ms(self, obj):
        if not obj.started_at or not obj.finished_at:
            return 0
        return max(0, int((obj.finished_at - obj.started_at).total_seconds() * 1000))


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


class AgentModelConfigSerializer(serializers.ModelSerializer):
    api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AgentModelConfig
        fields = [
            "id",
            "name",
            "provider",
            "api_key",
            "api_key_masked",
            "base_url",
            "model_name",
            "max_tokens",
            "temperature",
            "top_p",
            "is_active",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "api_key": {"write_only": True},
        }

    def get_api_key_masked(self, obj):
        if not obj.api_key:
            return ""
        if len(obj.api_key) <= 7:
            return "*" * len(obj.api_key)
        return f"{obj.api_key[:3]}{'*' * (len(obj.api_key) - 7)}{obj.api_key[-4:]}"

    def validate(self, attrs):
        if self.instance is None:
            required_fields = ["name", "provider", "api_key", "base_url", "model_name"]
            missing = [field for field in required_fields if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(f"缺少必填字段: {', '.join(missing)}")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and getattr(request, "user", None) and request.user.is_authenticated:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class AgentModelConfigPreviewSerializer(serializers.Serializer):
    api_key = serializers.CharField(required=True, allow_blank=False)
    base_url = serializers.CharField(required=True, allow_blank=False)
    model_name = serializers.CharField(required=True, allow_blank=False)
    temperature = serializers.FloatField(required=False, default=0.3)
    top_p = serializers.FloatField(required=False, default=0.9)
    max_tokens = serializers.IntegerField(required=False, default=256)
