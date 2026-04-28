import time
import uuid
from types import SimpleNamespace

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AgentMessage, AgentModelConfig, AgentSession
from .serializers import (
    AgentMessageSerializer,
    AgentModelConfigPreviewSerializer,
    AgentModelConfigSerializer,
    AgentSessionSerializer,
)
from .services import (
    PresetRegistry,
    ToolRegistry,
    build_user_prompt,
    call_model_structured,
    compose_answer,
    get_agent_runtime_status,
    get_short_term_memory,
    sync_builtin_docs,
)


class IsAgentConfigAdmin(permissions.BasePermission):
    message = "仅管理员可操作全局助手配置"

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


class AgentStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_agent_runtime_status())


class AgentSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AgentSessionSerializer

    def get_queryset(self):
        return AgentSession.objects.filter(user=self.request.user).order_by("-updated_at")

    def create(self, request, *args, **kwargs):
        title = request.data.get("title", "")
        session = AgentSession.objects.create(
            user=request.user,
            session_id=request.data.get("session_id") or f"sess_{uuid.uuid4().hex}",
            title=title[:500],
            preset_code="general_qa",
        )
        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        session = self.get_object()
        data = AgentMessageSerializer(session.messages.all(), many=True).data
        return Response(data)


class AgentChatViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    preset_registry = PresetRegistry()
    tool_registry = ToolRegistry()

    @action(detail=False, methods=["post"])
    def send_message(self, request):
        turn_start = time.perf_counter()
        text = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")
        route_context = request.data.get("route_context") or {}
        if not text:
            return Response({"error": "message不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        runtime_status = get_agent_runtime_status()
        if not runtime_status["model_configured"]:
            return Response(
                {
                    "error": "全局助手未配置可用模型，请到 配置中心 -> 全局助手配置 完成模型配置。",
                    "code": "MODEL_NOT_CONFIGURED",
                },
                status=status.HTTP_409_CONFLICT,
            )

        session = None
        if session_id:
            session = AgentSession.objects.filter(session_id=session_id, user=request.user).first()
        if not session:
            title = text[:20] + ("..." if len(text) > 20 else "")
            session = AgentSession.objects.create(
                user=request.user,
                session_id=f"sess_{uuid.uuid4().hex}",
                title=title,
            )

        preset = self.preset_registry.choose_preset(text)
        session.preset_code = preset
        session.save(update_fields=["preset_code", "updated_at"])

        user_message = AgentMessage.objects.create(
            session=session,
            role="user",
            content=text,
            metadata={"route_context": route_context},
        )
        assistant_message = AgentMessage.objects.create(
            session=session,
            role="assistant",
            content="",
            metadata={},
        )

        tool_exec = self.tool_registry.execute(
            preset_code=preset,
            session=session,
            assistant_message=assistant_message,
            user=request.user,
            message=text,
            route_context=route_context,
        )
        memory_messages = get_short_term_memory(
            session,
            exclude_message_ids=[user_message.id, assistant_message.id],
            limit=8,
        )
        user_prompt = build_user_prompt(
            user_message=text,
            route_context=route_context,
            memory_messages=memory_messages,
            tool_result=tool_exec.tool_result,
            citations=tool_exec.citations,
        )
        llm_result = call_model_structured(
            AgentModelConfig.get_active_config(),
            self.preset_registry.get_system_prompt(preset),
            user_prompt,
        )

        answer = compose_answer(text, preset, tool_exec.citations, tool_exec.tool_result, llm_result=llm_result)
        total_duration_ms = int((time.perf_counter() - turn_start) * 1000)
        failure_reason = (
                tool_exec.failure_reason
                or (llm_result.get("error") if llm_result.get("llm_called") and not llm_result.get(
            "llm_success") else "")
                or ""
        )
        trace = {
            "turn_id": f"turn_{uuid.uuid4().hex}",
            "preset_code": preset,
            "llm_called": bool(llm_result.get("llm_called")),
            "llm_success": bool(llm_result.get("llm_success")),
            "llm_model": llm_result.get("llm_model") or "",
            "tool_name": tool_exec.tool_name or "",
            "tool_status": tool_exec.tool_status,
            "total_duration_ms": total_duration_ms,
            "llm_duration_ms": int(llm_result.get("duration_ms") or 0),
            "tool_duration_ms": int(tool_exec.duration_ms or 0),
            "failure_reason": failure_reason,
        }
        assistant_message.content = answer
        assistant_message.metadata = {
            "preset": preset,
            "tool_result": tool_exec.tool_result,
            "citations": tool_exec.citations,
            "route_context_snapshot": route_context,
            "trace": trace,
        }
        assistant_message.save(update_fields=["content", "metadata"])
        session.save(update_fields=["updated_at"])

        return Response(
            {
                "session": AgentSessionSerializer(session).data,
                "preset_used": preset,
                "user_message": AgentMessageSerializer(user_message).data,
                "assistant_message": AgentMessageSerializer(assistant_message).data,
            }
        )

    @action(detail=False, methods=["post"])
    def sync_builtin_docs(self, request):
        if not IsAgentConfigAdmin().has_permission(request, self):
            return Response({"error": "仅管理员可同步平台文档"}, status=status.HTTP_403_FORBIDDEN)
        result = sync_builtin_docs()
        return Response(result)


class AgentModelConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAgentConfigAdmin]
    serializer_class = AgentModelConfigSerializer
    queryset = AgentModelConfig.objects.all().order_by("-updated_at")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        update_data = request.data.copy()
        raw_api_key = update_data.get("api_key")
        if not raw_api_key or ("*" in str(raw_api_key)):
            update_data.pop("api_key", None)
        serializer = self.get_serializer(instance, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="test_connection")
    def test_connection_preview(self, request):
        serializer = AgentModelConfigPreviewSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        config = SimpleNamespace(
            model_name=payload["model_name"],
            base_url=payload["base_url"],
            api_key=payload["api_key"],
            temperature=payload["temperature"],
            top_p=payload["top_p"],
            max_tokens=payload["max_tokens"],
        )
        llm_result = call_model_structured(config, "你是连接测试助手。", "请只回复：连接成功")
        if llm_result.get("llm_success"):
            return Response(
                {"success": True, "message": "连接测试成功", "duration_ms": llm_result.get("duration_ms", 0)})
        return Response(
            {
                "success": False,
                "message": llm_result.get("error") or "连接测试失败",
                "duration_ms": llm_result.get("duration_ms", 0),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="test_connection")
    def test_connection(self, request, pk=None):
        config = self.get_object()
        llm_result = call_model_structured(config, "你是连接测试助手。", "请只回复：连接成功")
        if llm_result.get("llm_success"):
            return Response(
                {"success": True, "message": "连接测试成功", "duration_ms": llm_result.get("duration_ms", 0)})
        return Response(
            {
                "success": False,
                "message": llm_result.get("error") or "连接测试失败",
                "duration_ms": llm_result.get("duration_ms", 0),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
