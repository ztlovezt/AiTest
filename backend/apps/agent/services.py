import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from django.db import models
from django.utils import timezone

from apps.data_factory.views import DataFactoryViewSet
from apps.projects.models import Project
from apps.testcases.models import TestCase
from .models import AgentBuiltinChunk, AgentBuiltinDocument, AgentMessage, AgentModelConfig, AgentToolCall

DEFAULT_MEMORY_LIMIT = 8
MAX_PROMPT_TEXT_CHARS = 4000
MAX_MEMORY_MESSAGE_CHARS = 260


def _truncate_text(text: str, max_chars: int = MAX_PROMPT_TEXT_CHARS) -> str:
    if not text:
        return ""
    clean = str(text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[:max_chars] + "..."


def _project_root() -> Path:
    # backend/apps/agent/services.py -> repo root
    return Path(__file__).resolve().parents[3]


def get_platform_doc_paths() -> List[Path]:
    root = _project_root()
    docs: List[Path] = []
    include_paths = [
        root / "README.md",
        root / "backend" / "apps" / "core" / "README.md",
        root / "frontend" / "PAGE_I18N_GUIDE.md",
    ]
    for path in include_paths:
        if path.exists():
            docs.append(path)
    backend_docs = root / "backend" / "docs"
    if backend_docs.exists():
        docs.extend(sorted(backend_docs.rglob("*.md")))
    return docs


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> List[str]:
    clean = text.strip()
    if not clean:
        return []
    chunks = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + size)
        chunks.append(clean[start:end])
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks


def sync_builtin_docs() -> Dict[str, int]:
    created = 0
    updated = 0
    total_chunks = 0
    active_paths = set()

    for path in get_platform_doc_paths():
        source_path = str(path.relative_to(_project_root()))
        active_paths.add(source_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        checksum = AgentBuiltinDocument.content_checksum(content)
        title = path.name
        doc, is_created = AgentBuiltinDocument.objects.get_or_create(
            source_path=source_path,
            defaults={
                "title": title,
                "content": content,
                "checksum": checksum,
                "is_active": True,
            },
        )
        if is_created:
            created += 1
        elif doc.checksum != checksum or not doc.is_active or doc.title != title:
            doc.title = title
            doc.content = content
            doc.checksum = checksum
            doc.is_active = True
            doc.save(update_fields=["title", "content", "checksum", "is_active", "updated_at"])
            updated += 1
        else:
            doc.is_active = True
            doc.save(update_fields=["is_active"])

        AgentBuiltinChunk.objects.filter(document=doc).delete()
        rows = []
        for idx, piece in enumerate(chunk_text(content)):
            rows.append(
                AgentBuiltinChunk(
                    document=doc,
                    chunk_index=idx,
                    content=piece,
                    token_count=max(1, len(piece) // 4),
                )
            )
        if rows:
            AgentBuiltinChunk.objects.bulk_create(rows, batch_size=500)
            total_chunks += len(rows)

    AgentBuiltinDocument.objects.exclude(source_path__in=active_paths).update(is_active=False)
    return {"created": created, "updated": updated, "chunks": total_chunks}


def get_agent_runtime_status() -> Dict[str, Any]:
    config = AgentModelConfig.get_active_config()
    docs_count = AgentBuiltinDocument.objects.filter(is_active=True).count()
    return {
        "model_configured": bool(config and config.base_url and config.api_key and config.model_name),
        "active_model_name": config.model_name if config else "",
        "docs_ready": docs_count > 0,
        "docs_count": docs_count,
    }


def search_platform_docs(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    terms = [token.lower() for token in query.split() if token.strip()]
    if not terms:
        return []
    queryset = AgentBuiltinChunk.objects.filter(document__is_active=True).select_related("document")
    scored: List[Tuple[float, AgentBuiltinChunk]] = []
    for chunk in queryset.iterator():
        content_lower = chunk.content.lower()
        score = 0.0
        for term in terms:
            if term in content_lower:
                score += 1.0 + content_lower.count(term) * 0.1
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    output: List[Dict[str, Any]] = []
    for score, chunk in scored[:top_k]:
        output.append(
            {
                "source_type": "platform_doc",
                "source_path": chunk.document.source_path,
                "title": chunk.document.title,
                "chunk_index": chunk.chunk_index,
                "score": round(score, 4),
                "content": chunk.content[:500],
            }
        )
    return output


def list_projects(user, keyword: str = "", limit: int = 10) -> Dict[str, Any]:
    queryset = Project.objects.filter(models.Q(owner=user) | models.Q(members=user)).distinct()
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)
    rows = queryset.order_by("name")[:limit]
    return {
        "projects": [{"id": item.id, "name": item.name, "status": item.status} for item in rows],
        "total": queryset.count(),
    }


def search_testcases(
    user, keyword: str = "", project_id: int = None, priority: str = "", test_type: str = "", limit: int = 10
) -> Dict[str, Any]:
    accessible_projects = Project.objects.filter(models.Q(owner=user) | models.Q(members=user)).distinct()
    queryset = TestCase.objects.filter(project__in=accessible_projects).select_related("project")
    if keyword:
        queryset = queryset.filter(models.Q(title__icontains=keyword) | models.Q(description__icontains=keyword))
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    if priority:
        queryset = queryset.filter(priority=priority)
    if test_type:
        queryset = queryset.filter(test_type=test_type)
    rows = queryset.order_by("-updated_at")[:limit]
    return {
        "testcases": [
            {
                "id": item.id,
                "title": item.title,
                "project_id": item.project_id,
                "project_name": item.project.name if item.project else "",
                "priority": item.priority,
                "test_type": item.test_type,
            }
            for item in rows
        ],
        "total": queryset.count(),
    }


def run_data_factory(tool_name: str, tool_category: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    viewset = DataFactoryViewSet()
    return viewset.execute_tool(tool_name, tool_category, input_data)


def _extract_project_id_from_route_context(route_context: Dict[str, Any]) -> Optional[int]:
    if not isinstance(route_context, dict):
        return None
    candidates = []
    scope = route_context.get("scope")
    if isinstance(scope, dict):
        candidates.append(scope.get("project_id"))
    candidates.append(route_context.get("project_id"))
    query = route_context.get("query")
    if isinstance(query, dict):
        candidates.append(query.get("project_id"))
    params = route_context.get("params")
    if isinstance(params, dict):
        candidates.append(params.get("project_id"))
    for value in candidates:
        if value in (None, "", []):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _is_testcase_lookup(message: str) -> bool:
    text = (message or "").strip().lower()
    return text.startswith("/testcases") or "用例" in message


def _parse_data_tool_command(message: str) -> Dict[str, Any]:
    raw = (message or "").replace("/data", "", 1).strip()
    if not raw:
        return {
            "ok": False,
            "error": "请使用 /data tool_name|tool_category|{\"key\":\"value\"} 格式，例如 /data format_json|json|{\"json_str\":\"{\\\"a\\\":1}\"}",
            "raw": raw,
        }
    parts = raw.split("|", 2)
    if len(parts) != 3:
        return {
            "ok": False,
            "error": "请使用 /data tool_name|tool_category|{\"key\":\"value\"} 格式，例如 /data format_json|json|{\"json_str\":\"{\\\"a\\\":1}\"}",
            "raw": raw,
        }
    tool_name = parts[0].strip()
    tool_category = parts[1].strip()
    payload_raw = parts[2].strip()
    if not tool_name or not tool_category:
        return {
            "ok": False,
            "error": "请使用 /data tool_name|tool_category|{\"key\":\"value\"} 格式，例如 /data format_json|json|{\"json_str\":\"{\\\"a\\\":1}\"}",
            "raw": raw,
        }
    try:
        input_data = json.loads(payload_raw)
        if not isinstance(input_data, dict):
            input_data = {"value": input_data}
    except json.JSONDecodeError:
        input_data = {"text": payload_raw}
    return {
        "ok": True,
        "tool_name": tool_name,
        "tool_category": tool_category,
        "input_data": input_data,
        "raw": raw,
    }


class PresetRegistry:
    def __init__(self):
        self._system_prompts = {
            "general_qa": "你是 TestHub 的全局助手。",
            "platform_help_qa": "你是 TestHub 的平台文档助手。优先使用平台内置文档引用回答。",
            "workspace_lookup": "你是 TestHub 的项目与测试资产查询助手。基于查询结果给出简洁结论。",
            "data_tool_helper": "你是 TestHub 的数据工具助手。基于工具执行结果解释用途和下一步。",
        }

    def choose_preset(self, message: str) -> str:
        text = (message or "").lower()
        if text.startswith("/docs") or "readme" in text or "使用说明" in message or "怎么" in message:
            return "platform_help_qa"
        if text.startswith("/projects") or text.startswith("/testcases") or "项目" in message or "用例" in message:
            return "workspace_lookup"
        if text.startswith("/data") or "json" in text or "base64" in text:
            return "data_tool_helper"
        return "general_qa"

    def get_system_prompt(self, preset_code: str) -> str:
        return self._system_prompts.get(preset_code, self._system_prompts["general_qa"])


@dataclass
class ToolExecutionResult:
    tool_name: str = ""
    tool_status: str = "skipped"
    tool_result: Dict[str, Any] = field(default_factory=dict)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    failure_reason: str = ""


class ToolRegistry:
    def execute(
            self,
            *,
            preset_code: str,
            session,
            assistant_message,
            user,
            message: str,
            route_context: Dict[str, Any],
    ) -> ToolExecutionResult:
        if preset_code == "platform_help_qa":
            return self._run_platform_docs(session, assistant_message, preset_code, message)
        if preset_code == "workspace_lookup":
            return self._run_workspace_lookup(session, assistant_message, preset_code, user, message, route_context)
        if preset_code == "data_tool_helper":
            return self._run_data_tool(session, assistant_message, preset_code, message)
        return ToolExecutionResult()

    def _run_platform_docs(self, session, assistant_message, preset_code: str, message: str) -> ToolExecutionResult:
        call, tool_result = create_tool_call(
            session=session,
            assistant_message=assistant_message,
            preset_code=preset_code,
            tool_name="search_platform_docs",
            arguments={"query": message, "top_k": 5},
            handler=lambda: {"results": search_platform_docs(message, top_k=5)},
        )
        citations = tool_result.get("results", [])
        return ToolExecutionResult(
            tool_name=call.tool_name,
            tool_status=call.status,
            tool_result=tool_result,
            citations=citations,
            duration_ms=_duration_ms(call.started_at, call.finished_at),
            failure_reason=call.error_message or "",
        )

    def _run_workspace_lookup(
            self, session, assistant_message, preset_code: str, user, message: str, route_context: Dict[str, Any]
    ) -> ToolExecutionResult:
        if _is_testcase_lookup(message):
            keyword = message.replace("/testcases", "").strip()
            kwargs = {"keyword": keyword, "limit": 10}
            project_id = _extract_project_id_from_route_context(route_context)
            if project_id:
                kwargs["project_id"] = project_id
            call, tool_result = create_tool_call(
                session=session,
                assistant_message=assistant_message,
                preset_code=preset_code,
                tool_name="search_testcases",
                arguments=kwargs,
                handler=lambda: search_testcases(user, **kwargs),
            )
        else:
            keyword = message.replace("/projects", "").strip()
            call, tool_result = create_tool_call(
                session=session,
                assistant_message=assistant_message,
                preset_code=preset_code,
                tool_name="list_projects",
                arguments={"keyword": keyword, "limit": 10},
                handler=lambda: list_projects(user, keyword=keyword, limit=10),
            )
        return ToolExecutionResult(
            tool_name=call.tool_name,
            tool_status=call.status,
            tool_result=tool_result,
            duration_ms=_duration_ms(call.started_at, call.finished_at),
            failure_reason=call.error_message or "",
        )

    def _run_data_tool(self, session, assistant_message, preset_code: str, message: str) -> ToolExecutionResult:
        parsed = _parse_data_tool_command(message)
        if not parsed.get("ok"):
            error_message = parsed.get("error") or "数据工具调用参数格式错误"
            failed_call = create_failed_tool_call(
                session=session,
                assistant_message=assistant_message,
                preset_code=preset_code,
                tool_name="run_data_factory",
                arguments={"raw": parsed.get("raw", "")},
                error_message=error_message,
                result={"error": error_message},
            )
            return ToolExecutionResult(
                tool_name=failed_call.tool_name,
                tool_status=failed_call.status,
                tool_result={"error": error_message},
                duration_ms=_duration_ms(failed_call.started_at, failed_call.finished_at),
                failure_reason=error_message,
            )
        tool_name = parsed["tool_name"]
        tool_category = parsed["tool_category"]
        input_data = parsed["input_data"]
        call, tool_result = create_tool_call(
            session=session,
            assistant_message=assistant_message,
            preset_code=preset_code,
            tool_name="run_data_factory",
            arguments={"tool_name": tool_name, "tool_category": tool_category, "input_data": input_data},
            handler=lambda: run_data_factory(tool_name, tool_category, input_data),
        )
        return ToolExecutionResult(
            tool_name=call.tool_name,
            tool_status=call.status,
            tool_result=tool_result,
            duration_ms=_duration_ms(call.started_at, call.finished_at),
            failure_reason=call.error_message or "",
        )


def choose_preset(message: str) -> str:
    return PresetRegistry().choose_preset(message)


def call_model_structured(config: AgentModelConfig, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    result = {
        "llm_called": False,
        "llm_success": False,
        "llm_model": config.model_name if config else "",
        "duration_ms": 0,
        "error": "",
        "content": "",
    }
    if not config or not config.base_url or not config.api_key or not config.model_name:
        result["error"] = "model_not_configured"
        return result
    start = time.perf_counter()
    result["llm_called"] = True
    base_url = config.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": config.model_name,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens": config.max_tokens,
    }
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        content = ""
        if choices:
            content = (choices[0].get("message") or {}).get("content", "").strip()
        result["content"] = content
        if content:
            result["llm_success"] = True
        else:
            result["error"] = "empty_response"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        result["duration_ms"] = int((time.perf_counter() - start) * 1000)
    return result


def get_short_term_memory(
        session, exclude_message_ids: Optional[List[int]] = None, limit: int = DEFAULT_MEMORY_LIMIT
) -> List[AgentMessage]:
    queryset = AgentMessage.objects.filter(session=session, role__in=["user", "assistant"]).order_by("-created_at")
    exclude_ids = [msg_id for msg_id in (exclude_message_ids or []) if msg_id]
    if exclude_ids:
        queryset = queryset.exclude(id__in=exclude_ids)
    rows = list(queryset[:limit])
    rows.reverse()
    return rows


def _format_short_term_memory(messages: List[AgentMessage]) -> str:
    if not messages:
        return "(无)"
    lines: List[str] = []
    for index, item in enumerate(messages, 1):
        role = "用户" if item.role == "user" else "助手"
        content = _truncate_text(item.content.replace("\n", " "), max_chars=MAX_MEMORY_MESSAGE_CHARS)
        lines.append(f"{index}. {role}: {content}")
    return "\n".join(lines)


def build_user_prompt(
        *,
        user_message: str,
        route_context: Dict[str, Any],
        memory_messages: List[AgentMessage],
        tool_result: Dict[str, Any],
        citations: List[Dict[str, Any]],
) -> str:
    route_snapshot = {
        "module": route_context.get("module") if isinstance(route_context, dict) else "",
        "path": route_context.get("path") if isinstance(route_context, dict) else "",
        "project_id": _extract_project_id_from_route_context(route_context or {}),
    }
    tool_summary = _truncate_text(json.dumps(tool_result or {}, ensure_ascii=False), max_chars=1000)
    citation_summary = _truncate_text(json.dumps((citations or [])[:3], ensure_ascii=False), max_chars=1000)
    memory_text = _format_short_term_memory(memory_messages)
    return (
        "短期记忆（最近8条）:\n"
        f"{memory_text}\n\n"
        "Route Context:\n"
        f"{json.dumps(route_snapshot, ensure_ascii=False)}\n\n"
        "本轮工具/引用摘要:\n"
        f"tool_result={tool_summary}\n"
        f"citations={citation_summary}\n\n"
        "当前用户问题:\n"
        f"{_truncate_text(user_message, max_chars=1200)}"
    )


def compose_answer(
        user_message: str,
        preset: str,
        citations: List[Dict[str, Any]],
        tool_result: Dict[str, Any],
        llm_result: Optional[Dict[str, Any]] = None,
) -> str:
    llm_content = (llm_result or {}).get("content", "").strip()
    if (llm_result or {}).get("llm_success") and llm_content:
        return llm_content

    if preset == "platform_help_qa":
        if citations:
            first = citations[0]
            return f"我在平台文档里找到了相关内容：{first['title']}（{first['source_path']}）。你可以继续问更具体的操作步骤。"
        return "暂时没在平台文档中检索到直接答案，建议你换一个更具体的关键词再问。"
    if preset == "workspace_lookup":
        if "projects" in tool_result:
            return f"已查询到 {tool_result.get('total', 0)} 个项目，已返回前 {len(tool_result.get('projects', []))} 条。"
        if "testcases" in tool_result:
            return f"已查询到 {tool_result.get('total', 0)} 条用例，已返回前 {len(tool_result.get('testcases', []))} 条。"
    if preset == "data_tool_helper":
        if "error" in tool_result:
            return f"数据工具执行失败：{tool_result.get('error')}"
        return "数据工具已执行，结果已附在本次消息中。"
    return "我已收到你的问题。V1 当前优先支持平台文档问答、项目/用例查询和部分数据工具调用。"


def create_tool_call(session, assistant_message, preset_code, tool_name, arguments, handler):
    call = AgentToolCall.objects.create(
        session=session,
        assistant_message=assistant_message,
        preset_code=preset_code,
        tool_name=tool_name,
        status="running",
        arguments=arguments or {},
        started_at=timezone.now(),
    )
    try:
        result = handler()
        call.result = result if isinstance(result, dict) else {"value": result}
        has_error = isinstance(result, dict) and bool(result.get("error"))
        call.status = "failed" if has_error else "success"
        call.error_message = str(result.get("error")) if has_error else ""
        call.finished_at = timezone.now()
        call.save(update_fields=["result", "status", "error_message", "finished_at"])
        return call, result
    except Exception as exc:
        call.status = "failed"
        call.error_message = str(exc)
        call.finished_at = timezone.now()
        call.save(update_fields=["status", "error_message", "finished_at"])
        return call, {"error": str(exc)}


def create_failed_tool_call(session, assistant_message, preset_code, tool_name, arguments, error_message, result=None):
    now = timezone.now()
    return AgentToolCall.objects.create(
        session=session,
        assistant_message=assistant_message,
        preset_code=preset_code,
        tool_name=tool_name,
        status="failed",
        arguments=arguments or {},
        result=result or {"error": error_message},
        error_message=error_message,
        started_at=now,
        finished_at=now,
    )


def _duration_ms(started_at, finished_at) -> int:
    if not started_at or not finished_at:
        return 0
    return max(0, int((finished_at - started_at).total_seconds() * 1000))
