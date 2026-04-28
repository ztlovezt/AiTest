from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AgentChatViewSet, AgentModelConfigViewSet, AgentSessionViewSet, AgentStatusView

router = DefaultRouter()
router.register(r"sessions", AgentSessionViewSet, basename="agent-sessions")
router.register(r"chat", AgentChatViewSet, basename="agent-chat")
router.register(r"configs", AgentModelConfigViewSet, basename="agent-configs")

urlpatterns = [
    path("status/", AgentStatusView.as_view(), name="agent-status"),
    path("", include(router.urls)),
]
