#!/usr/bin/env python3
"""测试环境 PrecisionRunRecord 数据初始化脚本。

用法::

    # 方式 1：直接运行（需确保 Django 环境已配置）
    cd backend && python ../tests/precision_testing/setup_run_records.py

    # 方式 2：在 pytest fixture 中调用
    from tests.precision_testing.setup_run_records import setup_run_records
    setup_run_records()

前置条件:
    - Django 后端已启动且数据库已迁移
    - 至少存在一个 RepoBinding 记录
    - 至少存在一个 ImpactAnalysis 记录（或自动创建）

数据说明:
    创建 4 条 PrecisionRunRecord，覆盖全部状态：
    1. completed + reduction_rate=0.756 + selected_testcases 非空
    2. failed + error_message 非空
    3. running + progress=45
    4. completed + selected_testcases=[]（空选中用例）
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django

django.setup()

import logging

from apps.precision_testing.models import (
    PrecisionRunRecord,
    ImpactAnalysis,
    CodeChangeAnalysis,
    RepoBinding,
)

logger = logging.getLogger(__name__)


def _ensure_dependencies() -> tuple[RepoBinding, CodeChangeAnalysis, ImpactAnalysis]:
    """确保测试依赖数据存在，返回 (repo_binding, change_analysis, impact_analysis)。"""
    binding = RepoBinding.objects.filter(is_active=True).first()
    if binding is None:
        raise RuntimeError("没有找到活跃的 RepoBinding，请先创建仓库绑定记录。")

    change_analysis = CodeChangeAnalysis.objects.filter(repo_binding=binding).first()
    if change_analysis is None:
        change_analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding,
            base_commit="abc1234" * 5 + "abc",
            head_commit="def5678" * 5 + "def",
            status="completed",
            changed_files=["src/foo.py", "src/bar.py"],
            changed_functions=["apps.foo:bar", "apps.bar:baz"],
        )
        logger.info("自动创建 CodeChangeAnalysis id=%s", change_analysis.id)

    impact_analysis = ImpactAnalysis.objects.filter(change_analysis=change_analysis).first()
    if impact_analysis is None:
        impact_analysis = ImpactAnalysis.objects.create(
            change_analysis=change_analysis,
            impacted_functions=["apps.foo:bar"],
            impacted_testcases=[1, 2, 3],
            min_regression_set=[1, 2],
            regression_time_estimate=300,
            status="completed",
        )
        logger.info("自动创建 ImpactAnalysis id=%s", impact_analysis.id)

    return binding, change_analysis, impact_analysis


def setup_run_records(clear_existing: bool = False) -> list[PrecisionRunRecord]:
    """创建/更新测试用的 PrecisionRunRecord 数据。

    Args:
        clear_existing: 是否先清空现有 PrecisionRunRecord 数据。

    Returns:
        创建的 PrecisionRunRecord 列表。
    """
    if clear_existing:
        deleted, _ = PrecisionRunRecord.objects.all().delete()
        logger.info("已清空 %d 条 PrecisionRunRecord", deleted)

    binding, change_analysis, impact_analysis = _ensure_dependencies()
    now = datetime.now()

    records_data = [
        {
            "impact_analysis": impact_analysis,
            "status": "completed",
            "total_testcases": 200,
            "reduction_rate": 0.756,
            "selected_testcases": [1, 2, 3, 4, 5],
            "progress": 100,
            "started_at": now - timedelta(hours=2),
            "completed_at": now - timedelta(hours=1),
            "error_message": "",
        },
        {
            "impact_analysis": impact_analysis,
            "status": "failed",
            "total_testcases": 50,
            "reduction_rate": 0.45,
            "selected_testcases": [10, 11],
            "progress": 60,
            "started_at": now - timedelta(days=2),
            "completed_at": now - timedelta(days=2) + timedelta(minutes=5),
            "error_message": "测试环境连接超时: neo4j connection refused",
        },
        {
            "impact_analysis": impact_analysis,
            "status": "running",
            "total_testcases": 80,
            "reduction_rate": 0.25,
            "selected_testcases": [20, 21, 22],
            "progress": 45,
            "started_at": now - timedelta(minutes=30),
            "completed_at": None,
            "error_message": "",
        },
        {
            "impact_analysis": impact_analysis,
            "status": "completed",
            "total_testcases": 50,
            "reduction_rate": 0.0,
            "selected_testcases": [],
            "progress": 100,
            "started_at": now - timedelta(days=1),
            "completed_at": now - timedelta(days=1) + timedelta(minutes=2),
            "error_message": "",
        },
    ]

    created_records: list[PrecisionRunRecord] = []
    for i, data in enumerate(records_data, start=1):
        record, was_created = PrecisionRunRecord.objects.update_or_create(
            impact_analysis=impact_analysis,
            status=data["status"],
            defaults=data,
        )
        created_records.append(record)
        action = "创建" if was_created else "更新"
        logger.info(
            "%s PrecisionRunRecord id=%s status=%s reduction_rate=%.3f",
            action, record.id, record.status, record.reduction_rate,
        )

    logger.info("PrecisionRunRecord 测试数据就绪: %d 条", len(created_records))
    return created_records


def verify_run_records() -> dict:
    """验证 PrecisionRunRecord 数据是否满足测试需求。"""
    stats = {
        "total": PrecisionRunRecord.objects.count(),
        "completed": PrecisionRunRecord.objects.filter(status="completed").count(),
        "failed": PrecisionRunRecord.objects.filter(status="failed").count(),
        "running": PrecisionRunRecord.objects.filter(status="running").count(),
        "has_error": PrecisionRunRecord.objects.exclude(error_message="").count(),
        "empty_selected": PrecisionRunRecord.objects.filter(selected_testcases=[]).count(),
        "ok": False,
    }
    stats["ok"] = (
        stats["completed"] >= 2
        and stats["failed"] >= 1
        and stats["running"] >= 1
        and stats["has_error"] >= 1
        and stats["empty_selected"] >= 1
    )
    logger.info("PrecisionRunRecord 验证结果: %s", stats)
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    clear = "--clear" in sys.argv
    try:
        setup_run_records(clear_existing=clear)
        stats = verify_run_records()
        if not stats["ok"]:
            logger.error("测试数据不满足要求，请检查依赖数据")
            sys.exit(1)
    except Exception as exc:
        logger.error("测试数据初始化失败: %s", exc)
        sys.exit(1)
