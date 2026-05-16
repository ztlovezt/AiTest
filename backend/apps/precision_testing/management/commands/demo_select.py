"""Week 4 收尾 demo: 离线演示最小回归集减少率。

用法::

    python manage.py demo_select                  # 默认 100 用例 / 时间预算 900s
    python manage.py demo_select --total 200      # 自定义总用例数
    python manage.py demo_select --budget 600     # 自定义时间预算
    python manage.py demo_select --json           # JSON 输出便于脚本/截图

设计目标:
    用户问 "Week 4 验收里那个 ≥40% 减少率到底什么样?" 时,跑一遍这个命令
    就能给出一组真实可截图的数字 (selected/total/reduction_rate),不需要拉
    起完整的 Neo4j + Git 仓库 + Django Q workers 。

合成数据分布 (覆盖三档分桶):
    * 5% critical  -> 必选层
    * 15% high     -> 候选层 (中高风险)
    * 30% medium   -> 候选层 (低中风险)
    * 50% low      -> 排除层

场景对照 §8.5.6 验收指标 "≥40% 减少率"。
"""
from __future__ import annotations

import json
import random
import sys
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Synthesize impact + risk records and print regression selection metrics"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--total", type=int, default=100, help="Total testcases to synthesize")
        parser.add_argument(
            "--budget", type=int, default=900, help="Time budget in seconds for selection"
        )
        parser.add_argument("--json", action="store_true", dest="as_json", help="JSON output")
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep generated records after demo (default: rollback)",
        )
        parser.add_argument(
            "--seed", type=int, default=42, help="RNG seed for reproducible demo numbers"
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
            RiskPredictionRecord,
        )
        from apps.precision_testing.regression_selector import RegressionSelector
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        total = int(options["total"])
        budget = int(options["budget"])
        as_json = bool(options["as_json"])
        keep = bool(options["keep"])
        seed = int(options["seed"])
        rng = random.Random(seed)

        if total < 4:
            self.stderr.write("--total must be >= 4")
            sys.exit(2)

        # 用 atomic + savepoint 让 --keep 可控,确保 demo 默认不污染真实数据
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                payload = self._run_demo(total, budget, as_json, rng)
            except Exception:
                transaction.savepoint_rollback(sid)
                raise
            else:
                if keep:
                    transaction.savepoint_commit(sid)
                else:
                    transaction.savepoint_rollback(sid)

        # 输出放在事务外部,避免事务回滚把日志缓冲一起冲掉
        if as_json:
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(self.style.SUCCESS("=== Week 4 Regression Selection Demo ==="))
            self.stdout.write(f"  Total testcases : {payload['total_testcases']}")
            self.stdout.write(
                f"  Selected        : {payload['selected']}  "
                f"(must_run={payload['must_run']} + candidate={payload['candidate']})"
            )
            self.stdout.write(f"  Excluded        : {payload['excluded']}")
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Reduction rate  : {payload['reduction_rate'] * 100:.2f}%   "
                    f"(target >= 40% per S8.5.6)"
                )
            )
            self.stdout.write(
                f"  Estimated time  : {payload['estimated_seconds']}s "
                f"/ budget {payload['time_budget']}s"
            )
            self.stdout.write(f"  Force full      : {payload['force_full']}")
            self.stdout.write(f"  Reason          : {payload['reason'] or '(empty)'}")
            if keep:
                self.stdout.write(self.style.WARNING("(demo records kept in DB)"))

    def _run_demo(self, total: int, budget: int, as_json: bool, rng: random.Random) -> dict:
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
            RiskPredictionRecord,
        )
        from apps.precision_testing.regression_selector import RegressionSelector
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        ts = int(timezone.now().timestamp())
        user, _ = User.objects.get_or_create(
            username=f"precision_demo_{ts}",
            defaults={"email": f"precision_demo_{ts}@example.com"},
        )
        project = Project.objects.create(name=f"PrecisionDemo_{ts}", owner=user)
        binding = RepoBinding.objects.create(
            project=project, repo_path=f"/tmp/demo_{ts}", default_branch="main"
        )
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding,
            base_commit="a" * 40,
            head_commit="b" * 40,
            status="completed",
        )

        # 按 5/15/30/50 比例分配优先级
        buckets = [
            ("critical", int(total * 0.05)),
            ("high", int(total * 0.15)),
            ("medium", int(total * 0.30)),
        ]
        buckets.append(("low", total - sum(c for _, c in buckets)))

        cases: list[TestCase] = []
        for priority, count in buckets:
            for i in range(count):
                cases.append(
                    TestCase.objects.create(
                        project=project,
                        title=f"demo_{priority}_{i}",
                        expected_result="ok",
                        author=user,
                        priority=priority,
                    )
                )
        assert len(cases) == total

        impact = ImpactAnalysis.objects.create(
            change_analysis=analysis,
            impacted_testcases=[c.id for c in cases],
            status="completed",
        )

        # 合成风险预测分数 — 与优先级正相关 + 噪声
        base_by_priority = {
            "critical": (0.85, 1.00),
            "high": (0.55, 0.80),
            "medium": (0.25, 0.55),
            "low": (0.00, 0.30),
        }
        level_for = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }
        for c in cases:
            lo, hi = base_by_priority[c.priority]
            score = round(rng.uniform(lo, hi), 3)
            RiskPredictionRecord.objects.create(
                impact_analysis=impact,
                testcase=c,
                risk_score=score,
                risk_level=level_for[c.priority],
                features={"priority": c.priority, "synthetic": True},
                model_version="heuristic-v1",
            )

        selector = RegressionSelector(impact_analysis=impact, time_budget_seconds=budget)
        result = selector.select()

        return {
            "total_testcases": result.total_testcases,
            "selected": len(result.selected_testcase_ids),
            "must_run": result.must_run_count,
            "candidate": result.candidate_count,
            "excluded": result.excluded_count,
            "reduction_rate": round(result.reduction_rate, 4),
            "estimated_seconds": result.estimated_seconds,
            "time_budget": budget,
            "force_full": result.force_full,
            "reason": result.reason,
        }
