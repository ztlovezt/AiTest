import json
import uuid

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AgentMessage, AgentSession
from .serializers import AgentMessageSerializer, AgentSessionSerializer
from .services import (
    choose_preset,
    compose_answer,
    create_tool_call,
    get_agent_runtime_status,
    list_projects,
    run_data_factory,
    search_platform_docs,
    search_testcases,
    sync_builtin_docs,
)


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

    @action(detail=False, methods=["post"])
    def send_message(self, request):
        text = (request.data.get("message") or "").strip()
        session_id = request.data.get("session_id")
        route_context = request.data.get("route_context") or {}
        if not text:
            return Response({"error": "message不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        runtime_status = get_agent_runtime_status()
        if not runtime_status["model_configured"]:
            return Response(
                {
                    "error": "全局助手未配置可用模型，请到 Django Admin -> 全局助手 -> Agent模型配置 启用配置。",
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

        preset = choose_preset(text)
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

        tool_result = {}
        citations = []
        if preset == "platform_help_qa":
            call, tool_result = create_tool_call(
                session=session,
                assistant_message=assistant_message,
                preset_code=preset,
                tool_name="search_platform_docs",
                arguments={"query": text, "top_k": 5},
                handler=lambda: {"results": search_platform_docs(text, top_k=5)},
            )
            citations = tool_result.get("results", [])
        elif preset == "workspace_lookup":
            if text.lower().startswith("/testcases") or "用例" in text:
                kwargs = {"keyword": text.replace("/testcases", "").strip(), "limit": 10}
                if route_context.get("project_id"):
                    kwargs["project_id"] = route_context.get("project_id")
                _, tool_result = create_tool_call(
                    session=session,
                    assistant_message=assistant_message,
                    preset_code=preset,
                    tool_name="search_testcases",
                    arguments=kwargs,
                    handler=lambda: search_testcases(request.user, **kwargs),
                )
            else:
                keyword = text.replace("/projects", "").strip()
                _, tool_result = create_tool_call(
                    session=session,
                    assistant_message=assistant_message,
                    preset_code=preset,
                    tool_name="list_projects",
                    arguments={"keyword": keyword, "limit": 10},
                    handler=lambda: list_projects(request.user, keyword=keyword, limit=10),
                )
        elif preset == "data_tool_helper":
            raw = text.replace("/data", "", 1).strip()
            tool_name = ""
            tool_category = ""
            input_data = {}
            if "|" in raw:
                parts = raw.split("|", 2)
                if len(parts) == 3:
                    tool_name = parts[0].strip()
                    tool_category = parts[1].strip()
                    try:
                        input_data = json.loads(parts[2].strip())
                    except json.JSONDecodeError:
                        input_data = {"text": parts[2].strip()}
            if not tool_name or not tool_category:
                tool_result = {
                    "error": "请使用 /data tool_name|tool_category|{\"key\":\"value\"} 格式，例如 /data format_json|json|{\"json_str\":\"{\\\"a\\\":1}\"}"
                }
            else:
                _, tool_result = create_tool_call(
                    session=session,
                    assistant_message=assistant_message,
                    preset_code=preset,
                    tool_name="run_data_factory",
                    arguments={"tool_name": tool_name, "tool_category": tool_category, "input_data": input_data},
                    handler=lambda: run_data_factory(tool_name, tool_category, input_data),
                )

        answer = compose_answer(text, preset, citations, tool_result)
        assistant_message.content = answer
        assistant_message.metadata = {
            "preset": preset,
            "tool_result": tool_result,
            "citations": citations,
            "route_context_snapshot": route_context,
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
        result = sync_builtin_docs()
        return Response(result)
