"""失效概率预测器 — XGBoost + 启发式冷启动"""
import logging
from typing import Any

from django.utils import timezone
from django.db.models import Count, Q

logger = logging.getLogger(__name__)


class RiskPredictor:
    """预测测试用例的失效概率(risk score)。

    冷启动阶段(历史数据 < 50 条)使用启发式规则;
    数据充足后切换 XGBoost 模型。
    """

    def __init__(self):
        self.model = None
        self._try_load_model()

    def _try_load_model(self) -> None:
        """尝试加载已训练的 XGBoost 模型。"""
        import os
        from django.conf import settings
        model_dir = getattr(settings, "PRECISION_TESTING", {}).get("model_path", "expand/models")
        model_file = os.path.join(model_dir, "risk_model.json")
        if os.path.exists(model_file):
            try:
                import xgboost as xgb
                self.model = xgb.XGBClassifier()
                self.model.load_model(model_file)
                logger.info("Loaded XGBoost risk model from %s", model_file)
            except Exception as exc:
                logger.warning("Failed to load model: %s", exc)

    def extract_features(self, testcase) -> dict[str, Any]:
        """从历史执行记录中提取特征向量。

        Features:
            - historical_failures: 历史失败次数
            - failure_rate: 失败率
            - days_since_last_change: 距上次修改天数
            - priority_score: 优先级分数(low=1,medium=2,high=3,critical=4)
            - has_code_mapping: 是否有代码映射(0/1)
            - testcase_age_days: 用例创建至今天数
        """
        from apps.executions.models import TestRunCase, TestRunCaseHistory

        # 历史失败统计
        total_runs = TestRunCase.objects.filter(testcase=testcase).count()
        failures = TestRunCaseHistory.objects.filter(
            run_case__testcase=testcase, status="failed"
        ).count()

        # 上次修改时间
        last_change = testcase.updated_at
        days_since_change = (timezone.now() - last_change).days

        priority_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        priority_score = priority_map.get(testcase.priority, 2)

        has_mapping = testcase.code_mappings.exists()
        age_days = (timezone.now() - testcase.created_at).days

        return {
            "historical_failures": failures,
            "failure_rate": round(failures / max(total_runs, 1), 3),
            "days_since_last_change": days_since_change,
            "priority_score": priority_score,
            "has_code_mapping": 1 if has_mapping else 0,
            "testcase_age_days": age_days,
        }

    def predict_heuristic(self, features: dict[str, Any]) -> float:
        """启发式规则计算风险分数(0.0-1.0)。

        加权公式:
            - failure_rate * 0.40
            - days_since_last_change 越近越高(max 30天) * 0.20
            - priority_score / 4 * 0.20
            - has_code_mapping == 0 ? 0.10 : 0.00
            - age < 7 天 ? 0.10 : 0.00 (新用例不稳定)
        """
        score = 0.0
        score += features["failure_rate"] * 0.40
        score += min(features["days_since_last_change"] / 30.0, 1.0) * 0.20
        score += (features["priority_score"] / 4.0) * 0.20
        if not features["has_code_mapping"]:
            score += 0.10
        if features["testcase_age_days"] < 7:
            score += 0.10
        return round(min(score, 1.0), 3)

    def predict(self, features: dict[str, Any]) -> float:
        """使用 XGBoost 模型预测(如可用)或回退到启发式。"""
        if self.model is None:
            return self.predict_heuristic(features)
        # Week 3: XGBoost 推理逻辑
        return self.predict_heuristic(features)

    @staticmethod
    def score_to_level(score: float) -> str:
        if score >= 0.8:
            return "critical"
        if score >= 0.6:
            return "high"
        if score >= 0.4:
            return "medium"
        return "low"
