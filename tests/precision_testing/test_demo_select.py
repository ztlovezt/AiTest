"""demo_select 管理命令单元测试。

覆盖目标:
    * 参数解析 (--total, --budget, --json, --keep, --seed)
    * 合成数据分布 (5/15/30/50 分桶)
    * 减少率计算与验收阈值 (>=40%)
    * --json 输出格式校验
    * --keep / 默认回滚行为
    * --total < 4 报错退出
    * 不同 seed 可复现性
"""
from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


# ---------------------------------------------------------------------------
# 参数解析与基本调用
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDemoSelectBasic:
    def test_default_run_prints_metrics(self) -> None:
        out = StringIO()
        err = StringIO()
        call_command("demo_select", stdout=out, stderr=err)
        text = out.getvalue()
        assert "Total testcases" in text
        assert "Selected" in text
        assert "Reduction rate" in text
        assert "target >= 40%" in text

    def test_total_200(self) -> None:
        out = StringIO()
        call_command("demo_select", "--total", "200", stdout=out)
        text = out.getvalue()
        assert "Total testcases : 200" in text

    def test_budget_custom(self) -> None:
        out = StringIO()
        call_command("demo_select", "--total", "50", "--budget", "60", stdout=out)
        text = out.getvalue()
        assert "budget 60s" in text or "budget 60" in text

    def test_total_too_small_exits_2(self) -> None:
        err = StringIO()
        with pytest.raises(SystemExit) as exc_info:
            call_command("demo_select", "--total", "3", stderr=err)
        assert exc_info.value.code == 2
        assert "--total must be >= 4" in err.getvalue()


# ---------------------------------------------------------------------------
# JSON 输出
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDemoSelectJson:
    def test_json_output_is_valid(self) -> None:
        out = StringIO()
        call_command("demo_select", "--total", "100", "--json", stdout=out)
        payload = json.loads(out.getvalue())
        assert "total_testcases" in payload
        assert "selected" in payload
        assert "must_run" in payload
        assert "candidate" in payload
        assert "excluded" in payload
        assert "reduction_rate" in payload
        assert "estimated_seconds" in payload
        assert "time_budget" in payload
        assert "force_full" in payload
        assert "reason" in payload

    def test_json_reduction_rate_above_threshold(self) -> None:
        out = StringIO()
        call_command("demo_select", "--total", "200", "--json", stdout=out)
        payload = json.loads(out.getvalue())
        # 5% critical + 15% high → must_run ≈ 20%
        # 剩余 80% 中 medium 按预算贪心选一部分
        # 整体缩减率应 >= 40%
        assert payload["reduction_rate"] >= 0.40

    def test_json_numbers_add_up(self) -> None:
        out = StringIO()
        call_command("demo_select", "--total", "100", "--json", stdout=out)
        payload = json.loads(out.getvalue())
        assert payload["selected"] == payload["must_run"] + payload["candidate"]
        assert payload["selected"] <= payload["total_testcases"]
        assert payload["excluded"] <= payload["total_testcases"]


# ---------------------------------------------------------------------------
# 可复现性 (seed)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDemoSelectReproducibility:
    def _run_json(self, seed: int) -> dict:
        out = StringIO()
        call_command("demo_select", "--total", "100", "--json", "--seed", str(seed), stdout=out)
        return json.loads(out.getvalue())

    def test_same_seed_same_result(self) -> None:
        a = self._run_json(42)
        b = self._run_json(42)
        assert a == b

    def test_different_seed_may_vary(self) -> None:
        """不同 seed 应产生结构相同但数值可能不同的结果。"""
        a = self._run_json(1)
        b = self._run_json(999)
        # 结构一致
        assert a.keys() == b.keys()
        assert a["total_testcases"] == b["total_testcases"]
        # 数值不一定相同(不强制断言差异,避免随机碰撞导致偶发失败)


# ---------------------------------------------------------------------------
# 数据保留 (--keep)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDemoSelectKeep:
    def test_default_rollback_no_records_persisted(self) -> None:
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        before_projects = set(Project.objects.values_list("id", flat=True))
        before_cases = set(TestCase.objects.values_list("id", flat=True))

        call_command("demo_select", "--total", "20", stdout=StringIO())

        after_projects = set(Project.objects.values_list("id", flat=True))
        after_cases = set(TestCase.objects.values_list("id", flat=True))

        assert after_projects == before_projects
        assert after_cases == before_cases

    def test_keep_persists_project_and_testcases(self) -> None:
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        before_projects = set(Project.objects.values_list("id", flat=True))
        call_command("demo_select", "--total", "20", "--keep", stdout=StringIO())
        after_projects = set(Project.objects.values_list("id", flat=True))

        assert len(after_projects) > len(before_projects)
        # demo 创建的 TestCase 也应保留
        assert TestCase.objects.count() >= 20


# ---------------------------------------------------------------------------
# 减少率验收
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDemoSelectReductionRate:
    @pytest.mark.parametrize("total", [50, 100, 200, 500])
    def test_reduction_rate_meets_target(self, total: int) -> None:
        out = StringIO()
        call_command("demo_select", "--total", str(total), "--json", stdout=out)
        payload = json.loads(out.getvalue())
        assert payload["reduction_rate"] >= 0.40, (
            f"total={total}: reduction_rate={payload['reduction_rate']} < 0.40"
        )

    def test_force_full_zero_reduction(self) -> None:
        """手动测试 force_full=True 时 reduction_rate=0 (通过直接调用 select)。"""
        from apps.precision_testing.models import (
            CodeChangeAnalysis,
            ImpactAnalysis,
            RepoBinding,
            RiskPredictionRecord,
        )
        from apps.precision_testing.regression_selector import RegressionSelector
        from apps.projects.models import Project
        from apps.testcases.models import TestCase
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="demo_force_full")
        project = Project.objects.create(name="DemoForceFull", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/ff")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)

        tc = TestCase.objects.create(
            project=project, title="ff_tc", expected_result="ok", priority="high", author=user
        )
        RiskPredictionRecord.objects.create(
            testcase=tc, impact_analysis=impact, risk_score=0.5, risk_level="high"
        )

        selector = RegressionSelector(
            impact, force_full=True, force_full_reason="integration test"
        )
        result = selector.select()
        assert result.reduction_rate == 0.0
        assert result.force_full is True
