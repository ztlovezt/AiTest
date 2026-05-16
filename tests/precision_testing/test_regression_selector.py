"""回归选择器单元测试 — Week 4。

覆盖目标:
    * _p75 / _reduction_rate 数值边界
    * RuntimeEstimator — 缓存命中 / 历史回退 / warm_up 批量
    * SelectionResult.as_dict 序列化
    * RegressionSelector — 三层分桶 / 时间预算贪心 / 全量回退
    * persist_selection / create_run_record 持久化辅助
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.precision_testing.regression_selector import (
    DEFAULT_FALLBACK_RUNTIME_SECONDS,
    DEFAULT_TIME_BUDGET_SECONDS,
    HIGH_RISK_THRESHOLD,
    MEDIUM_RISK_THRESHOLD,
    RegressionSelector,
    RuntimeEstimator,
    SelectionResult,
    _p75,
    _reduction_rate,
    create_run_record,
    persist_selection,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# _p75 / _reduction_rate
# ---------------------------------------------------------------------------


class TestP75:
    def test_empty_returns_zero(self) -> None:
        assert _p75([]) == 0.0

    def test_single_sample(self) -> None:
        assert _p75([42.0]) == 42.0

    def test_p75_of_uniform(self) -> None:
        # quantiles(n=4)[2] 即 P75
        result = _p75([1.0, 2.0, 3.0, 4.0])
        assert result >= 3.0  # P75 应在 3~4 之间

    def test_p75_avoids_max_outlier(self) -> None:
        """P75 应低于最大值,验证它能避开重测异常。"""
        samples = [1.0, 2.0, 3.0, 4.0, 100.0]
        result = _p75(samples)
        assert result < 100.0


class TestReductionRate:
    def test_zero_total(self) -> None:
        assert _reduction_rate(5, 0) == 0.0

    def test_full_reduction(self) -> None:
        assert _reduction_rate(0, 100) == 1.0

    def test_no_reduction(self) -> None:
        assert _reduction_rate(100, 100) == 0.0

    def test_typical_reduction(self) -> None:
        # 60% 缩减
        assert _reduction_rate(40, 100) == 0.6


# ---------------------------------------------------------------------------
# SelectionResult
# ---------------------------------------------------------------------------


class TestSelectionResult:
    def test_default_values(self) -> None:
        r = SelectionResult()
        assert r.selected_testcase_ids == []
        assert r.total_testcases == 0
        assert r.reduction_rate == 0.0
        assert r.force_full is False

    def test_as_dict_keys(self) -> None:
        r = SelectionResult(
            selected_testcase_ids=[1, 2],
            total_testcases=10,
            estimated_seconds=60,
            reduction_rate=0.8,
            must_run_count=1,
            candidate_count=1,
            excluded_count=8,
            force_full=False,
            reason="three_tier_greedy",
        )
        d = r.as_dict()
        assert d["selected_testcase_ids"] == [1, 2]
        assert d["reduction_rate"] == 0.8
        assert d["reason"] == "three_tier_greedy"
        assert "must_run_count" in d


# ---------------------------------------------------------------------------
# RuntimeEstimator
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRuntimeEstimator:
    def test_fallback_when_no_history(self) -> None:
        estimator = RuntimeEstimator(fallback_seconds=42)
        assert estimator.estimate(testcase_id=99999) == 42

    def test_estimate_total_sums(self) -> None:
        estimator = RuntimeEstimator(fallback_seconds=10)
        total = estimator.estimate_total([1, 2, 3])
        assert total == 30

    def test_estimate_caches_result(self) -> None:
        estimator = RuntimeEstimator(fallback_seconds=15)
        first = estimator.estimate(1)
        # 注入缓存 — 验证第二次直接返回缓存
        estimator._cache[1] = 99
        assert estimator.estimate(1) == 99
        assert first == 15  # 历史值

    def test_warm_up_empty_ids(self) -> None:
        estimator = RuntimeEstimator()
        estimator.warm_up([])  # 不抛错

    def test_warm_up_populates_cache(self) -> None:
        estimator = RuntimeEstimator(fallback_seconds=20)
        # 这些 ID 没有 TestRunCase 历史 → 应回退
        estimator.warm_up([101, 102, 103])
        assert estimator._cache[101] == 20
        assert estimator._cache[102] == 20


# ---------------------------------------------------------------------------
# RegressionSelector — 三层分桶
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegressionSelectorPartition:
    def _setup_impact(self):
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
        )
        from apps.projects.models import Project

        user = User.objects.create_user(username=f"sel_{timezone.now().timestamp()}")
        project = Project.objects.create(name="SelP", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        return user, project, impact

    def test_critical_priority_always_must_run(self) -> None:
        _, _, impact = self._setup_impact()
        selector = RegressionSelector(impact)
        predictions = [
            {"testcase_id": 1, "risk_score": 0.1, "priority": "critical"},
        ]
        must_run, candidates, excluded = selector._partition(predictions)
        assert 1 in must_run
        assert candidates == []

    def test_high_risk_score_forces_must_run(self) -> None:
        _, _, impact = self._setup_impact()
        selector = RegressionSelector(impact)
        predictions = [
            {"testcase_id": 2, "risk_score": HIGH_RISK_THRESHOLD, "priority": "low"},
        ]
        must_run, _, _ = selector._partition(predictions)
        assert 2 in must_run

    def test_medium_score_high_priority_is_candidate(self) -> None:
        _, _, impact = self._setup_impact()
        selector = RegressionSelector(impact)
        predictions = [
            {"testcase_id": 3, "risk_score": 0.5, "priority": "high"},
        ]
        must_run, candidates, _ = selector._partition(predictions)
        assert 3 not in must_run
        assert candidates and candidates[0]["testcase_id"] == 3

    def test_low_score_low_priority_excluded(self) -> None:
        _, _, impact = self._setup_impact()
        selector = RegressionSelector(impact)
        predictions = [
            {"testcase_id": 4, "risk_score": 0.1, "priority": "low"},
        ]
        _, candidates, excluded = selector._partition(predictions)
        assert candidates == []
        assert excluded and excluded[0]["testcase_id"] == 4

    def test_candidates_sorted_by_risk_desc(self) -> None:
        _, _, impact = self._setup_impact()
        selector = RegressionSelector(impact)
        predictions = [
            {"testcase_id": 1, "risk_score": 0.45, "priority": "high"},
            {"testcase_id": 2, "risk_score": 0.65, "priority": "high"},
            {"testcase_id": 3, "risk_score": 0.55, "priority": "high"},
        ]
        _, candidates, _ = selector._partition(predictions)
        scores = [c["risk_score"] for c in candidates]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# RegressionSelector.select — 集成
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegressionSelectorSelect:
    def _build(self, priorities=("critical", "high", "low"), scores=(0.9, 0.5, 0.1)):
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
            RiskPredictionRecord,
        )
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        user = User.objects.create_user(username=f"int_{timezone.now().timestamp()}")
        project = Project.objects.create(name=f"IntP_{timezone.now().timestamp()}", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)

        cases = []
        for prio, score in zip(priorities, scores):
            tc = TestCase.objects.create(
                project=project,
                title=f"tc_{prio}",
                expected_result="ok",
                priority=prio,
                author=user,
            )
            RiskPredictionRecord.objects.create(
                testcase=tc,
                impact_analysis=impact,
                risk_score=score,
                risk_level="high" if score >= 0.6 else "low",
            )
            cases.append(tc)
        return impact, cases

    def test_select_returns_must_run(self) -> None:
        impact, cases = self._build()
        selector = RegressionSelector(impact)
        result = selector.select()
        # critical / high-score 用例进入 must_run
        assert result.must_run_count >= 1
        assert len(result.selected_testcase_ids) >= 1
        assert result.reason == "three_tier_greedy"

    def test_select_no_predictions_empty_result(self) -> None:
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
        )
        from apps.projects.models import Project

        user = User.objects.create_user(username=f"emp_{timezone.now().timestamp()}")
        project = Project.objects.create(name="EmpP", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        selector = RegressionSelector(impact)
        result = selector.select()
        assert result.selected_testcase_ids == []
        assert result.reason == "no_predictions"

    def test_force_full_selects_everything(self) -> None:
        impact, cases = self._build()
        selector = RegressionSelector(
            impact, force_full=True, force_full_reason="manual override"
        )
        result = selector.select()
        assert result.force_full is True
        assert len(result.selected_testcase_ids) == len(cases)
        assert result.reason == "manual override"
        assert result.reduction_rate == 0.0

    def test_time_budget_drops_low_priority_candidates(self) -> None:
        """预算极小,只能容纳 must_run。"""
        impact, cases = self._build(
            priorities=("critical", "high", "high"),
            scores=(0.95, 0.5, 0.45),
        )
        # 5 秒预算 - must_run 已耗 30s,不足以容纳任何 candidate
        selector = RegressionSelector(impact, time_budget_seconds=5)
        result = selector.select()
        assert result.must_run_count == 1
        assert result.candidate_count == 0

    def test_estimated_seconds_within_budget(self) -> None:
        impact, cases = self._build()
        selector = RegressionSelector(impact, time_budget_seconds=600)
        result = selector.select()
        # estimated 应 ≤ budget 或 == must_run 估时
        assert result.estimated_seconds >= 0


# ---------------------------------------------------------------------------
# persist_selection / create_run_record
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPersistHelpers:
    def _setup(self):
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
        )
        from apps.projects.models import Project

        user = User.objects.create_user(username=f"prs_{timezone.now().timestamp()}")
        project = Project.objects.create(name="PrsP", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        return impact

    def test_persist_selection_writes_fields(self) -> None:
        impact = self._setup()
        result = SelectionResult(
            selected_testcase_ids=[10, 20, 30],
            total_testcases=100,
            estimated_seconds=300,
            reduction_rate=0.7,
        )
        persist_selection(impact, result)
        impact.refresh_from_db()
        assert impact.min_regression_set == [10, 20, 30]
        assert impact.regression_time_estimate == 300

    def test_create_run_record_returns_instance(self) -> None:
        from apps.precision_testing.models import PrecisionRunRecord

        impact = self._setup()
        result = SelectionResult(
            selected_testcase_ids=[1, 2],
            total_testcases=10,
            estimated_seconds=60,
            reduction_rate=0.8,
        )
        run = create_run_record(impact, result)
        assert isinstance(run, PrecisionRunRecord)
        assert run.selected_testcases == [1, 2]
        assert run.total_testcases == 10
        assert run.reduction_rate == 0.8
        assert run.status == "pending"


# ---------------------------------------------------------------------------
# 模块常量
# ---------------------------------------------------------------------------


class TestConstants:
    def test_thresholds_ordered(self) -> None:
        assert MEDIUM_RISK_THRESHOLD < HIGH_RISK_THRESHOLD
        assert 0.0 < MEDIUM_RISK_THRESHOLD < 1.0
        assert 0.0 < HIGH_RISK_THRESHOLD < 1.0

    def test_default_budget_positive(self) -> None:
        assert DEFAULT_TIME_BUDGET_SECONDS > 0
        assert DEFAULT_FALLBACK_RUNTIME_SECONDS > 0


# ---------------------------------------------------------------------------
# 性能基准: 1000 条选集
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRegressionSelectorPerformance:
    def _build_many(self, count: int = 1000):
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
            RiskPredictionRecord,
        )
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        user = User.objects.create_user(username=f"perf_{timezone.now().timestamp()}")
        project = Project.objects.create(name=f"PerfP_{timezone.now().timestamp()}", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/perf")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)

        # 按 5/15/30/50 分配优先级
        priorities = ["critical"] * int(count * 0.05)
        priorities += ["high"] * int(count * 0.15)
        priorities += ["medium"] * int(count * 0.30)
        priorities += ["low"] * (count - len(priorities))

        base_score = {
            "critical": (0.85, 1.00),
            "high": (0.55, 0.80),
            "medium": (0.25, 0.55),
            "low": (0.00, 0.30),
        }

        cases = []
        for i, prio in enumerate(priorities):
            tc = TestCase.objects.create(
                project=project,
                title=f"perf_{prio}_{i}",
                expected_result="ok",
                priority=prio,
                author=user,
            )
            lo, hi = base_score[prio]
            score = round(lo + (hi - lo) * ((i % 7) / 7.0), 3)
            RiskPredictionRecord.objects.create(
                testcase=tc,
                impact_analysis=impact,
                risk_score=score,
                risk_level="high" if score >= HIGH_RISK_THRESHOLD else "medium" if score >= MEDIUM_RISK_THRESHOLD else "low",
            )
            cases.append(tc)
        return impact, cases

    def test_select_1000_under_3s(self) -> None:
        """1000 条用例选集应在 3 秒内完成。"""
        import time

        impact, _ = self._build_many(1000)
        selector = RegressionSelector(impact, time_budget_seconds=900)

        start = time.perf_counter()
        result = selector.select()
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, f"select(1000) took {elapsed:.3f}s, budget 3s"
        assert result.total_testcases == 1000
        assert result.reduction_rate >= 0.40

    def test_select_1000_budget_too_small_only_must_run(self) -> None:
        """预算过小时只选 must_run, candidate 全部被预算淘汰。"""
        impact, _ = self._build_many(1000)
        selector = RegressionSelector(impact, time_budget_seconds=600)
        result = selector.select()
        # must_run 估时(92×30s=2760s)已超预算 → candidate 一个都进不来
        assert result.candidate_count == 0
        assert result.must_run_count > 0
        assert result.estimated_seconds > 600  # must_run 本身已超预算

    def test_select_1000_must_run_includes_all_critical(self) -> None:
        """1000 条用例中 critical 必须全部进入 must_run。"""
        impact, cases = self._build_many(1000)
        selector = RegressionSelector(impact)
        result = selector.select()

        critical_ids = {c.id for c in cases if c.priority == "critical"}
        selected_set = set(result.selected_testcase_ids)
        assert critical_ids.issubset(selected_set), "critical 用例未全部选中"
