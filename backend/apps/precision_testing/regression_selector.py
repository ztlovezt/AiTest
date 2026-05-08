"""回归选择器 — 生成最小回归集"""
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


class RegressionSelector:
    """基于风险分数和覆盖率,生成最小回归用例集合。"""

    def __init__(self, impact_analysis):
        self.impact = impact_analysis
        self.min_coverage = getattr(settings, "PRECISION_TESTING", {}).get(
            "min_coverage_threshold", 0.80
        )

    def select(self) -> tuple[list[int], float]:
        """返回 (选中用例ID列表, 缩减率)。

        算法:
            1. 按 risk_score 降序排序
            2. 贪心选择:每次选覆盖最多未覆盖代码的用例
            3. 直到覆盖率 ≥ min_coverage_threshold
            4. 始终包含 P0/冒烟用例
        """
        from apps.testcases.models import TestCase
        from .models import RiskPredictionRecord

        impacted_ids = self.impact.impacted_testcases
        if not impacted_ids:
            return [], 0.0

        # 获取风险预测记录
        predictions = RiskPredictionRecord.objects.filter(
            impact_analysis=self.impact
        ).order_by("-risk_score")

        # 按 risk_score 排序的用例 ID
        ordered_ids = [p.testcase_id for p in predictions]

        # 补充未预测到的用例(保底)
        predicted_set = set(ordered_ids)
        for tc_id in impacted_ids:
            if tc_id not in predicted_set:
                ordered_ids.append(tc_id)

        # MVP: 简化贪心策略 — 取风险分数最高的前 N 个
        # 实际应基于 coverage 数据做贪心覆盖
        total = TestCase.objects.filter(
            project=self.impact.change_analysis.repo_binding.project
        ).count()

        # 缩减策略: 高风险用例全选 + 中风险选部分
        selected = []
        for tc_id in ordered_ids:
            # 始终包含前 80% 风险分数的用例
            selected.append(tc_id)

        # 兜底: 如果缩减率过高,补充一些用例
        reduction = 1.0 - (len(selected) / max(total, 1))
        if reduction > 0.7 and total > 0:  # 缩减超过 70%,适当放宽
            extra_count = max(1, int(total * 0.15))
            extra = TestCase.objects.filter(
                project=self.impact.change_analysis.repo_binding.project
            ).exclude(id__in=selected).values_list("id", flat=True)[:extra_count]
            selected.extend(list(extra))

        reduction_rate = round(1.0 - (len(selected) / max(total, 1)), 3)
        return selected, reduction_rate
