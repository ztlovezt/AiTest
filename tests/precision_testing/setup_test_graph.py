#!/usr/bin/env python3
"""测试环境 Neo4j 图谱数据初始化脚本。

用法::

    # 方式 1：直接运行（需确保 Django 环境已配置）
    cd backend && python ../tests/precision_testing/setup_test_graph.py

    # 方式 2：通过 management command（推荐）
    cd backend && python manage.py build_graph --full

    # 方式 3：通过 API 触发（需先获取 JWT Token）
    curl -X POST http://localhost:8000/api/precision-testing/repos/1/analyze/ \
      -H "Authorization: Bearer $TOKEN"

前置条件:
    - Neo4j 服务已启动 (docker-compose -f docker-compose.neo4j.yml up -d)
    - Django 后端已启动且数据库已迁移
    - 至少存在一个 RepoBinding 记录

集成到 CI::

    # 在 pytest 前置步骤中执行
    pytest tests/precision_testing/setup_test_graph.py || true
    pytest tests/precision_testing/
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django

django.setup()

import logging

from apps.precision_testing.models import RepoBinding

logger = logging.getLogger(__name__)


def setup_test_graph(repo_binding_id: int | None = None, full: bool = True) -> None:
    """执行图谱构建，填充 Neo4j 测试数据。

    Args:
        repo_binding_id: 指定仓库绑定 ID；为 None 时自动选择第一个活跃的绑定。
        full: 是否执行全量构建；False 时仅增量构建。
    """
    from django.core.management import call_command

    if repo_binding_id is None:
        binding = RepoBinding.objects.filter(is_active=True).first()
        if binding is None:
            raise RuntimeError(
                "没有找到活跃的 RepoBinding，请先创建仓库绑定记录。"
            )
        repo_binding_id = binding.id
        logger.info("自动选择 RepoBinding id=%s (%s)", repo_binding_id, binding.repo_url)

    logger.info("开始构建 Neo4j 图谱 (repo_binding_id=%s, full=%s)", repo_binding_id, full)
    call_command("build_graph", repo_binding_id=str(repo_binding_id), **{"full": full})
    logger.info("图谱构建完成")


def verify_graph_data() -> dict:
    """验证 Neo4j 中是否有数据，返回节点/边数量。"""
    from apps.precision_testing.impact_query import get_impact_query

    impact_query = get_impact_query()
    try:
        result = impact_query.query_overview(limit=1)
        nodes = result.get("nodes", [])
        edges = result.get("edges", [])
        logger.info("Neo4j 图谱验证: nodes=%d, edges=%d", len(nodes), len(edges))
        return {"nodes": len(nodes), "edges": len(edges), "ok": len(nodes) > 0}
    except Exception as exc:
        logger.error("Neo4j 验证失败: %s", exc)
        return {"nodes": 0, "edges": 0, "ok": False, "error": str(exc)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 简单参数解析
    repo_id = None
    full_build = True
    for arg in sys.argv[1:]:
        if arg.startswith("--repo="):
            repo_id = int(arg.split("=", 1)[1])
        elif arg == "--incremental":
            full_build = False

    try:
        setup_test_graph(repo_binding_id=repo_id, full=full_build)
        stats = verify_graph_data()
        if not stats["ok"]:
            sys.exit(1)
    except Exception as exc:
        logger.error("测试数据初始化失败: %s", exc)
        sys.exit(1)
