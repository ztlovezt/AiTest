import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from django.db import models
from django.utils import timezone

from apps.data_factory.views import DataFactoryViewSet
from apps.projects.models import Project
from apps.testcases.models import TestCase

from .models import AgentBuiltinChunk, AgentBuiltinDocument, AgentModelConfig, AgentToolCall


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


def choose_preset(message: str) -> str:
    text = message.lower()
    if text.startswith("/docs") or "readme" in text or "使用说明" in message or "怎么" in message:
        return "platform_help_qa"
    if text.startswith("/projects") or text.startswith("/testcases") or "项目" in message or "用例" in message:
        return "workspace_lookup"
    if text.startswith("/data") or "json" in text or "base64" in text:
        return "data_tool_helper"
    return "general_qa"


def _call_model(config: AgentModelConfig, system_prompt: str, user_prompt: str) -> str:
    if not config or not config.base_url or not config.api_key or not config.model_name:
        return ""
    base_url = config.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": config.model_name,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "temperature": config.temperature,
        "top_p": config.top_p,
        "max_tokens": config.max_tokens,
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    return (choices[0].get("message") or {}).get("content", "").strip()


def compose_answer(
    user_message: str, preset: str, citations: List[Dict[str, Any]], tool_result: Dict[str, Any]
) -> str:
    config = AgentModelConfig.get_active_config()
    summary = ""
    if tool_result:
        summary = json.dumps(tool_result, ensure_ascii=False)[:1600]
    if citations:
        summary = json.dumps(citations[:3], ensure_ascii=False)[:1600]
    prompt = (
        f"用户问题: {user_message}\n"
        f"当前预设: {preset}\n"
        f"可用上下文摘要: {summary}\n"
        "请输出简洁中文回答，必要时给出下一步建议。"
    )
    try:
        llm_answer = _call_model(config, "你是 TestHub 的全局助手。", prompt)
    except Exception:
        llm_answer = ""
    if llm_answer:
        return llm_answer

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
        call.result = result
        call.status = "success"
        call.finished_at = timezone.now()
        call.save(update_fields=["result", "status", "finished_at"])
        return call, result
    except Exception as exc:
        call.status = "failed"
        call.error_message = str(exc)
        call.finished_at = timezone.now()
        call.save(update_fields=["status", "error_message", "finished_at"])
        return call, {"error": str(exc)}
