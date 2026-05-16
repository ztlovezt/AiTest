"""回归选择器 — 最小回归集生成

Week 4 升级要点:
    - 三层选集策略:
        * 必选层: P0(critical) 用例 + 风险分数 ≥ HIGH_THRESHOLD
        * 候选层: P1(high) 用例 + MEDIUM_THRESHOLD ≤ 风险 < HIGH_THRESHOLD
        * 排除层: P2/P3 + 风险 < MEDIUM_THRESHOLD(可被 force_full 覆盖)
    - 时间预算约束(默认 900s,贪心选择最大化风险收益)
    - RuntimeEstimator 基于历史 P75 估算,无历史时回退到默认值
    - 「全量回退」开关 force_full=True 用于安全网
    - 与 ImpactAnalysis / RiskPredictionRecord 完整衔接

设计参考:
    - 《精准测试设计策略方案及执行计划》§7.4 最小回归集算法
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 常量与默认配置
# ---------------------------------------------------------------------------

DEFAULT_TIME_BUDGET_SECONDS = 900       # 15 分钟
DEFAULT_FALLBACK_RUNTIME_SECONDS = 30   # 单条用例无历史时的估时
HIGH_RISK_THRESHOLD = 0.7
MEDIUM_RISK_THRESHOLD = 0.4
MUST_RUN_PRIORITIES_DEFAULT = ("critical",)
CANDIDATE_PRIORITIES_DEFAULT = ("high", "medium")


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class SelectionResult:
    """选集结果。"""

    selected_testcase_ids: list[int] = field(default_factory=list)
    total_testcases: int = 0
    estimated_seconds: int = 0
    reduction_rate: float = 0.0
    must_run_count: int = 0
    candidate_count: int = 0
    excluded_count: int = 0
    force_full: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_testcase_ids": self.selected_testcase_ids,
            "total_testcases": self.total_testcases,
            "estimated_seconds": self.estimated_seconds,
            "reduction_rate": self.reduction_rate,
            "must_run_count": self.must_run_count,
            "candidate_count": self.candidate_count,
            "excluded_count": self.excluded_count,
            "force_full": self.force_full,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# RuntimeEstimator(运行时估算)
# ---------------------------------------------------------------------------


class RuntimeEstimator:
    """从 TestRunCase.elapsed_time 历史估算用例耗时。

    策略:
        - 取最近 N 次成功执行的 P75 时长(避开重测异常)
        - 缺乏历史时使用 DEFAULT_FALLBACK_RUNTIME_SECONDS
        - 缓存所有用例的估算结果,避免反复查询
    """

    def __init__(
        self,
        fallback_seconds: int = DEFAULT_FALLBACK_RUNTIME_SECONDS,
        history_window: int = 10,
    ) -> None:
        self.fallback = fallback_seconds
        self.history_window = history_window
        self._cache: dict[int, int] = {}

    def estimate(self, testcase_id: int) -> int:
        """单条用例的耗时估算(秒)。"""
        if testcase_id in self._cache:
            return self._cache[testcase_id]
        seconds = self._compute(testcase_id)
        self._cache[testcase_id] = seconds
        return seconds

    def estimate_total(self, testcase_ids: list[int]) -> int:
        return sum(self.estimate(tid) for tid in testcase_ids)

    def warm_up(self, testcase_ids: list[int]) -> None:
        """批量预热缓存,减少 ORM 查询次数。"""
        try:
            from apps.executions.models import TestRunCase
        except ImportError:
            return
        runs = (
            TestRunCase.objects.filter(testcase_id__in=testcase_ids, status="passed")
            .exclude(elapsed_time__isnull=True)
            .order_by("testcase_id", "-executed_at")
            .values("testcase_id", "elapsed_time")
        )
        grouped: dict[int, list[float]] = {}
        for row in runs:
            tid = row["testcase_id"]
            grouped.setdefault(tid, []).append(row["elapsed_time"].total_seconds())
        for tid in testcase_ids:
            samples = grouped.get(tid, [])[: self.history_window]
            if not samples:
                self._cache[tid] = self.fallback
            else:
                self._cache[tid] = max(int(_p75(samples)), 1)

    def _compute(self, testcase_id: int) -> int:
        try:
            from apps.executions.models import TestRunCase
        except ImportError:
            return self.fallback
        runs = (
            TestRunCase.objects.filter(testcase_id=testcase_id, status="passed")
            .exclude(elapsed_time__isnull=True)
            .order_by("-executed_at")[: self.history_window]
        )
        samples = [r.elapsed_time.total_seconds() for r in runs if r.elapsed_time]
        if not samples:
            return self.fallback
        return max(int(_p75(samples)), 1)


def _p75(samples: list[float]) -> float:
    """计算 P75 — 不引入 numpy。"""
    if not samples:
        return 0.0
    if len(samples) == 1:
        return samples[0]
    return statistics.quantiles(samples, n=4)[2]


# ---------------------------------------------------------------------------
# RegressionSelector(选集核心)
# ---------------------------------------------------------------------------


class RegressionSelector:
    """基于风险分数 + 时间预算的最小回归集生成。

    输入:
        - impact_analysis: ImpactAnalysis 实例
        - 自动从 RiskPredictionRecord 拉取该 impact 的所有预测

    输出:
        - SelectionResult(selected_ids, reduction_rate, estimated_seconds, ...)
    """

    def __init__(
        self,
        impact_analysis,
        time_budget_seconds: int | None = None,
        force_full: bool = False,
        force_full_reason: str = "",
        estimator: RuntimeEstimator | None = None,
    ) -> None:
        self.impact = impact_analysis
        self.time_budget = time_budget_seconds or _get_default_time_budget()
        self.force_full = force_full
        self.force_full_reason = force_full_reason
        self.estimator = estimator or RuntimeEstimator()

    # ---- 主入口 ---------------------------------------------------------

    def select(self) -> SelectionResult:
        """执行选集并返回结果。"""
        from apps.testcases.models import TestCase

        project = self.impact.change_analysis.repo_binding.project
        total_count = TestCase.objects.filter(project=project).count()

        if self.force_full:
            return self._select_full(project, total_count)

        predictions = self._load_predictions()
        if not predictions:
            return self._empty_result(total_count, reason="no_predictions")

        # 三层分桶
        must_run_ids, candidates, excluded = self._partition(predictions)

        # 预热估时缓存
        all_candidate_ids = list(must_run_ids) + [p["testcase_id"] for p in candidates]
        self.estimator.warm_up(all_candidate_ids)

        # 时间预算贪心选择
        selected = list(must_run_ids)
        used_time = self.estimator.estimate_total(selected)
        for p in candidates:
            cost = self.estimator.estimate(p["testcase_id"])
            if used_time + cost <= self.time_budget:
                selected.append(p["testcase_id"])
                used_time += cost

        reduction = _reduction_rate(len(selected), total_count)
        return SelectionResult(
            selected_testcase_ids=selected,
            total_testcases=total_count,
            estimated_seconds=used_time,
            reduction_rate=reduction,
            must_run_count=len(must_run_ids),
            candidate_count=len(selected) - len(must_run_ids),
            excluded_count=len(excluded),
            force_full=False,
            reason="three_tier_greedy",
        )

    # ---- 内部辅助 -------------------------------------------------------

    def _select_full(self, project, total_count: int) -> SelectionResult:
        """全量回退 — 选所有用例。"""
        from apps.testcases.models import TestCase

        all_ids = list(
            TestCase.objects.filter(project=project).values_list("id", flat=True)
        )
        self.estimator.warm_up(all_ids)
        used_time = self.estimator.estimate_total(all_ids)
        return SelectionResult(
            selected_testcase_ids=all_ids,
            total_testcases=total_count,
            estimated_seconds=used_time,
            reduction_rate=0.0,
            must_run_count=len(all_ids),
            candidate_count=0,
            excluded_count=0,
            force_full=True,
            reason=self.force_full_reason or "force_full_invoked",
        )

    def _load_predictions(self) -> list[dict[str, Any]]:
        """从 RiskPredictionRecord 加载该 impact 的预测,join testcase.priority。"""
        from .models import RiskPredictionRecord

        rows = (
            RiskPredictionRecord.objects.filter(impact_analysis=self.impact)
            .select_related("testcase")
            .order_by("-risk_score")
            .values("testcase_id", "risk_score", "testcase__priority")
        )
        return [
            {
                "testcase_id": r["testcase_id"],
                "risk_score": r["risk_score"],
                "priority": r["testcase__priority"] or "medium",
            }
            for r in rows
        ]

    def _partition(
        self, predictions: list[dict[str, Any]]
    ) -> tuple[list[int], list[dict[str, Any]], list[dict[str, Any]]]:
        """三层分桶:必选 / 候选 / 排除。

        - 必选: priority in MUST_RUN_PRIORITIES OR risk_score ≥ HIGH_THRESHOLD
        - 候选: priority in CANDIDATE_PRIORITIES AND
                MEDIUM_THRESHOLD ≤ risk_score < HIGH_THRESHOLD
        - 排除: 其他
        """
        must_priorities = set(_get_must_run_priorities())
        candidate_priorities = set(_get_candidate_priorities())

        must_run: list[int] = []
        candidates: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        seen_must: set[int] = set()

        for p in predictions:
            tid = p["testcase_id"]
            score = p["risk_score"]
            prio = p["priority"]

            if prio in must_priorities or score >= HIGH_RISK_THRESHOLD:
                if tid not in seen_must:
                    must_run.append(tid)
                    seen_must.add(tid)
                continue

            if (
                prio in candidate_priorities
                and MEDIUM_RISK_THRESHOLD <= score < HIGH_RISK_THRESHOLD
            ):
                candidates.append(p)
                continue

            excluded.append(p)

        # 候选层按风险降序排
        candidates.sort(key=lambda p: -p["risk_score"])
        return must_run, candidates, excluded

    def _empty_result(self, total: int, reason: str) -> SelectionResult:
        return SelectionResult(
            selected_testcase_ids=[],
            total_testcases=total,
            estimated_seconds=0,
            reduction_rate=1.0 if total > 0 else 0.0,
            must_run_count=0,
            candidate_count=0,
            excluded_count=0,
            force_full=False,
            reason=reason,
        )


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _reduction_rate(selected: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(1.0 - selected / total, 3)


def _get_default_time_budget() -> int:
    cfg = getattr(settings, "PRECISION_TESTING", {}) or {}
    return cfg.get("max_regression_time_seconds", DEFAULT_TIME_BUDGET_SECONDS)


def _get_must_run_priorities() -> tuple[str, ...]:
    cfg = getattr(settings, "PRECISION_TESTING", {}) or {}
    raw = cfg.get("must_run_priorities", MUST_RUN_PRIORITIES_DEFAULT)
    return tuple(raw) if raw else MUST_RUN_PRIORITIES_DEFAULT


def _get_candidate_priorities() -> tuple[str, ...]:
    cfg = getattr(settings, "PRECISION_TESTING", {}) or {}
    raw = cfg.get("candidate_priorities", CANDIDATE_PRIORITIES_DEFAULT)
    return tuple(raw) if raw else CANDIDATE_PRIORITIES_DEFAULT


# ---------------------------------------------------------------------------
# 持久化辅助
# ---------------------------------------------------------------------------


def persist_selection(impact_analysis, result: SelectionResult) -> None:
    """将选集结果写入 ImpactAnalysis.min_regression_set / regression_time_estimate。"""
    impact_analysis.min_regression_set = result.selected_testcase_ids
    impact_analysis.regression_time_estimate = result.estimated_seconds
    impact_analysis.save(update_fields=["min_regression_set", "regression_time_estimate"])


def create_run_record(impact_analysis, result: SelectionResult, run_plan=None):
    """创建 PrecisionRunRecord。"""
    from .models import PrecisionRunRecord

    return PrecisionRunRecord.objects.create(
        impact_analysis=impact_analysis,
        selected_testcases=result.selected_testcase_ids,
        total_testcases=result.total_testcases,
        reduction_rate=result.reduction_rate,
        run_plan=run_plan,
        status="pending",
    )
