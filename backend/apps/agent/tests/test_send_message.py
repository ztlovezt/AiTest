from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.agent.models import (
    AgentBuiltinChunk,
    AgentBuiltinDocument,
    AgentMessage,
    AgentModelConfig,
    AgentSession,
    AgentToolCall,
)
from apps.projects.models import Project
from apps.testcases.models import TestCase as CaseModel
from apps.users.models import User

SEND_URL = "/api/agent/chat/send_message/"


def llm_ok(content="LLM_OK"):
    return {
        "llm_called": True,
        "llm_success": True,
        "llm_model": "mock-model",
        "duration_ms": 11,
        "error": "",
        "content": content,
    }


class AgentSendMessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", password="pwd12345")
        self.other_user = User.objects.create_user(username="u2", password="pwd12345")
        self.client.force_authenticate(self.user)

    def create_active_model(self):
        return AgentModelConfig.objects.create(
            name="default",
            provider="openai_compatible",
            api_key="test-key",
            base_url="http://mock-llm.local/v1",
            model_name="mock-model",
            is_active=True,
            created_by=self.user,
        )

    @patch("apps.agent.views.call_model_structured")
    def test_send_message_success_create_and_reuse_session_with_trace(self, mock_llm):
        self.create_active_model()
        project = Project.objects.create(name="Alpha", owner=self.user, status="active")
        mock_llm.return_value = llm_ok("项目查询已完成")

        first = self.client.post(SEND_URL, {"message": "/projects alpha"}, format="json")
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()

        session_id = first_payload["session"]["session_id"]
        self.assertTrue(session_id.startswith("sess_"))
        self.assertEqual(first_payload["preset_used"], "workspace_lookup")
        self.assertEqual(AgentSession.objects.count(), 1)
        self.assertEqual(AgentMessage.objects.filter(session__session_id=session_id).count(), 2)
        self.assertEqual(AgentToolCall.objects.filter(session__session_id=session_id).count(), 1)

        assistant_metadata = first_payload["assistant_message"]["metadata"]
        self.assertIn("trace", assistant_metadata)
        trace = assistant_metadata["trace"]
        self.assertTrue(str(trace["turn_id"]).startswith("turn_"))
        self.assertEqual(trace["preset_code"], "workspace_lookup")
        self.assertTrue(trace["llm_called"])
        self.assertTrue(trace["llm_success"])
        self.assertEqual(trace["llm_model"], "mock-model")
        self.assertEqual(trace["tool_name"], "list_projects")
        self.assertEqual(trace["tool_status"], "success")
        self.assertGreaterEqual(trace["total_duration_ms"], 0)
        self.assertGreaterEqual(trace["llm_duration_ms"], 0)
        self.assertGreaterEqual(trace["tool_duration_ms"], 0)
        self.assertEqual(trace["failure_reason"], "")

        second = self.client.post(
            SEND_URL,
            {"message": "/projects alpha again", "session_id": session_id},
            format="json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["session"]["session_id"], session_id)
        self.assertEqual(AgentSession.objects.count(), 1)
        self.assertEqual(AgentMessage.objects.filter(session__session_id=session_id).count(), 4)
        self.assertEqual(project.name, "Alpha")

    def test_model_not_configured_returns_409_and_no_messages_or_tool_calls(self):
        resp = self.client.post(SEND_URL, {"message": "hello"}, format="json")
        self.assertEqual(resp.status_code, 409)
        payload = resp.json()
        self.assertEqual(payload["code"], "MODEL_NOT_CONFIGURED")
        self.assertEqual(AgentSession.objects.count(), 0)
        self.assertEqual(AgentMessage.objects.count(), 0)
        self.assertEqual(AgentToolCall.objects.count(), 0)

    @patch("apps.agent.views.call_model_structured")
    def test_docs_search_returns_citations_and_success_tool_call(self, mock_llm):
        self.create_active_model()
        doc = AgentBuiltinDocument.objects.create(
            source_path="README.md",
            title="README",
            content="TestHub 文档：全局助手使用说明",
            checksum=AgentBuiltinDocument.content_checksum("TestHub 文档：全局助手使用说明"),
            is_active=True,
        )
        AgentBuiltinChunk.objects.create(
            document=doc,
            chunk_index=0,
            content="这里有 TestHub 平台文档与使用说明示例",
            token_count=10,
        )
        mock_llm.return_value = llm_ok("文档回答")

        resp = self.client.post(SEND_URL, {"message": "/docs TestHub 使用说明"}, format="json")
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        citations = payload["assistant_message"]["metadata"]["citations"]
        self.assertGreaterEqual(len(citations), 1)
        self.assertEqual(citations[0]["source_path"], "README.md")

        tool_call = AgentToolCall.objects.latest("created_at")
        self.assertEqual(tool_call.tool_name, "search_platform_docs")
        self.assertEqual(tool_call.status, "success")

    @patch("apps.agent.views.call_model_structured")
    @patch("apps.agent.services.run_data_factory")
    def test_tool_calls_testcase_and_data_command_with_invalid_format_failure(self, mock_run_data_factory, mock_llm):
        self.create_active_model()
        mock_llm.return_value = llm_ok("工具调用完成")
        mock_run_data_factory.return_value = {"ok": True, "value": {"a": 1}}

        project = Project.objects.create(name="P1", owner=self.user, status="active")
        CaseModel.objects.create(
            project=project,
            title="登录成功",
            description="登录验证",
            expected_result="登录成功",
            author=self.user,
            priority="medium",
            test_type="functional",
            status="active",
        )

        testcase_resp = self.client.post(
            SEND_URL,
            {
                "message": "/testcases 登录",
                "route_context": {"scope": {"project_id": str(project.id)}},
            },
            format="json",
        )
        self.assertEqual(testcase_resp.status_code, 200)
        testcase_tool = testcase_resp.json()["assistant_message"]["metadata"]["tool_result"]
        self.assertEqual(testcase_tool["total"], 1)
        self.assertEqual(testcase_tool["testcases"][0]["title"], "登录成功")

        data_ok_resp = self.client.post(
            SEND_URL,
            {"message": '/data format_json|json|{"json_str":"{\\"a\\":1}"}'},
            format="json",
        )
        self.assertEqual(data_ok_resp.status_code, 200)
        data_ok_trace = data_ok_resp.json()["assistant_message"]["metadata"]["trace"]
        self.assertEqual(data_ok_trace["tool_name"], "run_data_factory")
        self.assertEqual(data_ok_trace["tool_status"], "success")

        bad_resp = self.client.post(SEND_URL, {"message": "/data bad-format"}, format="json")
        self.assertEqual(bad_resp.status_code, 200)
        bad_trace = bad_resp.json()["assistant_message"]["metadata"]["trace"]
        self.assertEqual(bad_trace["tool_name"], "run_data_factory")
        self.assertEqual(bad_trace["tool_status"], "failed")
        self.assertTrue(bad_trace["failure_reason"])
        bad_tool_call = AgentToolCall.objects.latest("created_at")
        self.assertEqual(bad_tool_call.status, "failed")
        self.assertIn("格式", bad_tool_call.error_message)

    @patch("apps.agent.views.call_model_structured")
    def test_permission_isolation_session_and_workspace_data(self, mock_llm):
        self.create_active_model()
        mock_llm.return_value = llm_ok("权限过滤校验")

        private_project = Project.objects.create(name="Private", owner=self.other_user, status="active")
        private_session = AgentSession.objects.create(user=self.other_user, title="others")
        AgentMessage.objects.create(session=private_session, role="user", content="hello", metadata={})
        CaseModel.objects.create(
            project=private_project,
            title="他人用例",
            description="",
            expected_result="ok",
            author=self.other_user,
            priority="medium",
            test_type="functional",
            status="active",
        )

        forbidden = self.client.get(f"/api/agent/sessions/{private_session.id}/messages/")
        self.assertEqual(forbidden.status_code, 404)

        project_resp = self.client.post(SEND_URL, {"message": "/projects"}, format="json")
        self.assertEqual(project_resp.status_code, 200)
        project_tool_result = project_resp.json()["assistant_message"]["metadata"]["tool_result"]
        self.assertEqual(project_tool_result["total"], 0)

        testcase_resp = self.client.post(
            SEND_URL,
            {"message": "/testcases 用例", "route_context": {"project_id": private_project.id}},
            format="json",
        )
        self.assertEqual(testcase_resp.status_code, 200)
        testcase_tool_result = testcase_resp.json()["assistant_message"]["metadata"]["tool_result"]
        self.assertEqual(testcase_tool_result["total"], 0)

    @patch("apps.agent.views.call_model_structured")
    def test_short_term_memory_only_keeps_recent_8_messages(self, mock_llm):
        self.create_active_model()
        session = AgentSession.objects.create(user=self.user, title="memory-test")

        for i in range(6):
            AgentMessage.objects.create(session=session, role="user", content=f"old-user-{i}", metadata={})
            AgentMessage.objects.create(session=session, role="assistant", content=f"old-assistant-{i}", metadata={})

        captured = {}

        def fake_llm(_config, _system_prompt, user_prompt):
            captured["user_prompt"] = user_prompt
            return llm_ok("记忆窗口校验")

        mock_llm.side_effect = fake_llm
        resp = self.client.post(
            SEND_URL,
            {"session_id": session.session_id, "message": "当前问题是什么？"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        prompt = captured["user_prompt"]

        self.assertNotIn("old-user-0", prompt)
        self.assertNotIn("old-assistant-0", prompt)
        self.assertIn("old-user-2", prompt)
        self.assertIn("old-assistant-5", prompt)
