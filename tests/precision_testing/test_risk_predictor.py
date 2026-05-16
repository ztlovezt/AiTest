"""风险预测器单元测试 — Week 4。

覆盖目标:
    * FeatureVector — as_dict/as_vector/不可变性
    * HeuristicScorer — 9 维加权 / 边界 / 批量
    * XGBoostScorer — 模型缺失降级 / 训练样本不足返回 None
    * FeatureExtractor — 各特征实现 / 默认值 / impact_paths 归一化
    * RiskPredictor — 编排 / persist / 默认 scorer 选择
    * score_to_level — 阈值划分
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.precision_testing.risk_predictor import (
    FeatureExtractor,
    FeatureVector,
    HEURISTIC_WEIGHTS,
    HeuristicScorer,
    PRIORITY_SCORE_MAP,
    PredictionResult,
    RiskPredictor,
    XGBoostScorer,
    _get_min_train_samples,
    score_to_level,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# FeatureVector
# ---------------------------------------------------------------------------


class TestFeatureVector:
    def test_default_values(self) -> None:
        f = FeatureVector()
        assert f.failure_rate == 0.0
        assert f.priority_score == 0.4  # medium 默认

    def test_as_dict_keys(self) -> None:
        f = FeatureVector(failure_rate=0.5, priority_score=1.0)
        d = f.as_dict()
        assert set(d.keys()) == set(HEURISTIC_WEIGHTS.keys())
        assert d["failure_rate"] == 0.5

    def test_as_vector_order_matches_weights(self) -> None:
        f = FeatureVector(
            failure_rate=0.1,
            recent_failure_streak=0.2,
            coverage_confidence=0.3,
            change_intensity=0.4,
            priority_score=0.5,
            days_since_last_change=0.6,
            has_code_mapping=0.7,
            testcase_age_days=0.8,
            impact_path_depth=0.9,
        )
        assert f.as_vector() == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    def test_immutability(self) -> None:
        f = FeatureVector(failure_rate=0.1)
        with pytest.raises(Exception):  # frozen dataclass
            f.failure_rate = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# HeuristicScorer
# ---------------------------------------------------------------------------


class TestHeuristicScorer:
    def test_zero_features_returns_zero(self) -> None:
        scorer = HeuristicScorer()
        assert scorer.predict(FeatureVector()) == pytest.approx(
            HEURISTIC_WEIGHTS["priority_score"] * 0.4, rel=0.01
        )

    def test_full_features_close_to_one(self) -> None:
        scorer = HeuristicScorer()
        f = FeatureVector(
            failure_rate=1.0,
            recent_failure_streak=1.0,
            coverage_confidence=1.0,
            change_intensity=1.0,
            priority_score=1.0,
            days_since_last_change=1.0,
            has_code_mapping=1.0,
            testcase_age_days=1.0,
            impact_path_depth=1.0,
        )
        assert scorer.predict(f) == 1.0

    def test_weights_sum_to_one(self) -> None:
        assert sum(HEURISTIC_WEIGHTS.values()) == pytest.approx(1.0)

    def test_high_failure_rate_dominates(self) -> None:
        scorer = HeuristicScorer()
        low = scorer.predict(FeatureVector(failure_rate=0.0))
        high = scorer.predict(FeatureVector(failure_rate=1.0))
        assert high > low

    def test_predict_batch_preserves_order(self) -> None:
        scorer = HeuristicScorer()
        features = [
            FeatureVector(failure_rate=0.0),
            FeatureVector(failure_rate=0.5),
            FeatureVector(failure_rate=1.0),
        ]
        scores = scorer.predict_batch(features)
        assert len(scores) == 3
        assert scores[0] < scores[1] < scores[2]

    def test_predict_clipped_to_max_one(self) -> None:
        scorer = HeuristicScorer(weights={k: 2.0 for k in HEURISTIC_WEIGHTS})
        f = FeatureVector(failure_rate=1.0)
        assert scorer.predict(f) == 1.0

    def test_version_is_heuristic(self) -> None:
        assert HeuristicScorer().version.startswith("heuristic-")


# ---------------------------------------------------------------------------
# XGBoostScorer (无模型时降级)
# ---------------------------------------------------------------------------


class TestXGBoostScorer:
    def test_missing_model_falls_back_to_heuristic(self, tmp_path) -> None:
        scorer = XGBoostScorer(model_path=str(tmp_path / "no_such.json"))
        assert scorer._model is None
        f = FeatureVector(failure_rate=0.5)
        score = scorer.predict(f)
        assert 0.0 <= score <= 1.0

    def test_predict_batch_falls_back(self, tmp_path) -> None:
        scorer = XGBoostScorer(model_path=str(tmp_path / "no_such.json"))
        features = [FeatureVector(failure_rate=0.0), FeatureVector(failure_rate=1.0)]
        scores = scorer.predict_batch(features)
        assert len(scores) == 2
        assert scores[0] < scores[1]

    def test_get_min_train_samples_reads_settings(self) -> None:
        with patch("apps.precision_testing.risk_predictor.settings") as mock_settings:
            mock_settings.PRECISION_TESTING = {"min_xgboost_training_samples": 500}
            assert _get_min_train_samples() == 500

    def test_get_min_train_samples_default(self) -> None:
        with patch("apps.precision_testing.risk_predictor.settings") as mock_settings:
            mock_settings.PRECISION_TESTING = {}
            assert _get_min_train_samples() == 1000

    def test_train_returns_none_when_samples_insufficient(self, tmp_path) -> None:
        result = XGBoostScorer.train(
            feature_matrix=[[0.0] * 9],
            labels=[1],
            save_to=str(tmp_path / "m.json"),
            min_samples=100,
        )
        assert result is None

    def test_empty_batch_returns_empty_list(self, tmp_path) -> None:
        scorer = XGBoostScorer(model_path=str(tmp_path / "no_such.json"))
        assert scorer.predict_batch([]) == []

    def test_default_model_path_reads_settings(self) -> None:
        import os as _os

        with patch("apps.precision_testing.risk_predictor.settings") as mock_settings:
            mock_settings.PRECISION_TESTING = {"model_path": "/tmp/models"}
            path = XGBoostScorer._default_model_path()
            expected = _os.path.join("/tmp/models", "risk_model.json")
            assert path == expected

    def test_predict_with_loaded_model(self, tmp_path) -> None:
        """mock xgboost 加载成功后的 predict 路径。"""
        model_path = str(tmp_path / "mock_model.json")
        scorer = XGBoostScorer(model_path=model_path)
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.3, 0.7]]
        scorer._model = mock_model
        score = scorer.predict(FeatureVector(failure_rate=0.5))
        assert score == 0.7

    def test_predict_batch_with_loaded_model(self, tmp_path) -> None:
        """mock xgboost 加载成功后的 predict_batch 路径。"""
        model_path = str(tmp_path / "mock_model.json")
        scorer = XGBoostScorer(model_path=model_path)
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = [[0.4, 0.6], [0.2, 0.8]]
        scorer._model = mock_model
        features = [FeatureVector(failure_rate=0.0), FeatureVector(failure_rate=1.0)]
        scores = scorer.predict_batch(features)
        assert scores == [0.6, 0.8]

    def test_predict_xgboost_exception_fallback(self, tmp_path) -> None:
        """xgboost predict 异常时降级到启发式。"""
        model_path = str(tmp_path / "mock_model.json")
        scorer = XGBoostScorer(model_path=model_path)
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = RuntimeError("boom")
        scorer._model = mock_model
        score = scorer.predict(FeatureVector(failure_rate=0.5))
        assert 0.0 <= score <= 1.0

    def test_predict_batch_xgboost_exception_fallback(self, tmp_path) -> None:
        """xgboost batch predict 异常时降级到启发式。"""
        model_path = str(tmp_path / "mock_model.json")
        scorer = XGBoostScorer(model_path=model_path)
        mock_model = MagicMock()
        mock_model.predict_proba.side_effect = RuntimeError("boom")
        scorer._model = mock_model
        features = [FeatureVector(failure_rate=0.0)]
        scores = scorer.predict_batch(features)
        assert len(scores) == 1
        assert 0.0 <= scores[0] <= 1.0

    def test_train_success_path(self, tmp_path) -> None:
        """mock xgboost 训练成功完整路径。"""
        xgb = pytest.importorskip("xgboost", reason="xgboost not installed")
        model_path = str(tmp_path / "trained.json")
        matrix = [[i / 10.0] * 9 for i in range(10)]
        labels = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        scorer = XGBoostScorer.train(
            feature_matrix=matrix,
            labels=labels,
            save_to=model_path,
            min_samples=5,
        )
        assert scorer is not None
        assert os.path.exists(model_path)
        assert scorer._model is not None

    def test_train_import_error_returns_none(self, tmp_path) -> None:
        with patch.dict("sys.modules", {"xgboost": None}):
            result = XGBoostScorer.train(
                feature_matrix=[[0.0] * 9],
                labels=[1],
                save_to=str(tmp_path / "m.json"),
                min_samples=1,
            )
            assert result is None

    def test_try_load_success_path(self, tmp_path) -> None:
        """mock xgboost 存在且模型文件存在时的加载路径。"""
        model_path = str(tmp_path / "model.json")
        # 创建一个空文件模拟模型
        with open(model_path, "w") as f:
            f.write('{"dummy": true}')
        with patch("apps.precision_testing.risk_predictor.os.path.exists", return_value=True):
            mock_xgb = MagicMock()
            mock_model = MagicMock()
            mock_xgb.XGBClassifier.return_value = mock_model
            with patch.dict("sys.modules", {"xgboost": mock_xgb}):
                scorer = XGBoostScorer(model_path=model_path)
                assert scorer._model is mock_model
                mock_model.load_model.assert_called_once_with(model_path)


# ---------------------------------------------------------------------------
# score_to_level
# ---------------------------------------------------------------------------


class TestScoreToLevel:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0.0, "low"),
            (0.39, "low"),
            (0.40, "medium"),
            (0.59, "medium"),
            (0.60, "high"),
            (0.79, "high"),
            (0.80, "critical"),
            (1.0, "critical"),
        ],
    )
    def test_thresholds(self, score: float, expected: str) -> None:
        assert score_to_level(score) == expected


# ---------------------------------------------------------------------------
# PRIORITY_SCORE_MAP
# ---------------------------------------------------------------------------


class TestPriorityMap:
    def test_critical_is_max(self) -> None:
        assert PRIORITY_SCORE_MAP["critical"] == 1.0

    def test_low_is_min(self) -> None:
        assert PRIORITY_SCORE_MAP["low"] == 0.2

    def test_priority_increases_monotonically(self) -> None:
        order = ["low", "medium", "high", "critical"]
        scores = [PRIORITY_SCORE_MAP[p] for p in order]
        assert scores == sorted(scores)


# ---------------------------------------------------------------------------
# FeatureExtractor (Django ORM 集成)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestFeatureExtractor:
    def _setup(self, priority="medium"):
        from apps.testcases.models import TestCase
        from apps.projects.models import Project

        user = User.objects.create_user(username=f"fx_{timezone.now().timestamp()}")
        project = Project.objects.create(name="FXP", owner=user)
        tc = TestCase.objects.create(
            project=project,
            title="t1",
            expected_result="ok",
            priority=priority,
            author=user,
        )
        return user, project, tc

    def test_priority_score_mapped(self) -> None:
        _, _, tc = self._setup(priority="critical")
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.priority_score == 1.0

    def test_no_history_zero_failure_rate(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.failure_rate == 0.0
        assert f.recent_failure_streak == 0.0

    def test_no_mappings_marker(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.has_code_mapping == 1.0  # 无映射 → 1.0(加风险)

    def test_with_mapping_lowers_no_mapping_marker(self) -> None:
        from apps.precision_testing.models import TestCaseCodeMapping

        _, _, tc = self._setup()
        TestCaseCodeMapping.objects.create(
            testcase=tc,
            function_signature="apps.x:f",
            file_path="x.py",
            mapping_type="manual",
            confidence=1.0,
        )
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.has_code_mapping == 0.0
        assert f.coverage_confidence == 1.0

    def test_new_testcase_age_marker(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        # 创建后立即测试,应被标记为新用例
        assert f.testcase_age_days == 1.0

    def test_change_intensity_from_change_analysis(self) -> None:
        from apps.precision_testing.models import RepoBinding, CodeChangeAnalysis

        user, project, _ = self._setup()
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding,
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=[
                {"path": "apps/x/views.py", "changed_lines": 50},
                {"path": "apps/x/models.py", "changed_lines": 30},
            ],
        )
        extractor = FeatureExtractor(change_analysis=analysis)
        f = extractor.extract(project.testcases.first() or _)  # type: ignore
        # 80 lines / 100 = 0.8
        assert f.change_intensity == 0.8

    def test_change_intensity_clipped_to_one(self) -> None:
        from apps.precision_testing.models import RepoBinding, CodeChangeAnalysis

        _, project, _ = self._setup()
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding,
            base_commit="a" * 40,
            head_commit="b" * 40,
            changed_files=[{"path": "x", "changed_lines": 5000}],
        )
        extractor = FeatureExtractor(change_analysis=analysis)
        tc = project.testcases.first()
        f = extractor.extract(tc)
        assert f.change_intensity == 1.0

    def test_impact_path_depth_normalized(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor(impact_paths={tc.id: 1})
        f = extractor.extract(tc)
        assert f.impact_path_depth == 1.0  # 直接调用 = 满分

    def test_impact_path_depth_deeper_lower(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor(impact_paths={tc.id: 3})
        f = extractor.extract(tc)
        assert 0.0 < f.impact_path_depth < 1.0

    def test_impact_path_depth_default_zero(self) -> None:
        _, _, tc = self._setup()
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.impact_path_depth == 0.0

    def test_extract_batch(self) -> None:
        _, project, _ = self._setup()
        from apps.testcases.models import TestCase

        # 创建额外用例
        user = User.objects.first()
        tc2 = TestCase.objects.create(
            project=project, title="t2", expected_result="ok", author=user
        )
        extractor = FeatureExtractor()
        cases = list(project.testcases.all())
        features = extractor.extract_batch(cases)
        assert len(features) == len(cases)

    def test_failure_rate_with_history(self) -> None:
        from apps.executions.models import TestPlan, TestRun, TestRunCase

        _, project, tc = self._setup()
        user = User.objects.first()
        plan = TestPlan.objects.create(name="hist", creator=user)
        plan.projects.add(project)
        # 每个 TestRunCase 需要独立的 TestRun(唯一约束 test_run+testcase)
        for i, status in enumerate(["passed", "failed", "passed"]):
            run = TestRun.objects.create(
                name=f"r{i}", test_plan=plan, project=project, creator=user, assignee=user, status="completed"
            )
            TestRunCase.objects.create(
                testcase=tc,
                test_run=run,
                status=status,
                executed_at=timezone.now(),
            )
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.failure_rate == pytest.approx(0.333, rel=0.01)

    def test_recent_failure_streak_with_runs(self) -> None:
        from apps.executions.models import TestPlan, TestRun, TestRunCase

        _, project, tc = self._setup()
        user = User.objects.first()
        plan = TestPlan.objects.create(name="streak", creator=user)
        plan.projects.add(project)
        # 最近 5 次: failed, failed, passed, failed, passed → streak = 2
        statuses = ["failed", "failed", "passed", "failed", "passed"]
        for i, status in enumerate(statuses):
            run = TestRun.objects.create(
                name=f"r{i}", test_plan=plan, project=project, creator=user, assignee=user, status="completed"
            )
            TestRunCase.objects.create(
                testcase=tc,
                test_run=run,
                status=status,
                executed_at=timezone.now() - timedelta(minutes=i),
            )
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.recent_failure_streak == pytest.approx(2 / 5, rel=0.01)

    def test_coverage_confidence_with_mappings(self) -> None:
        from apps.precision_testing.models import TestCaseCodeMapping

        _, _, tc = self._setup()
        TestCaseCodeMapping.objects.create(
            testcase=tc,
            function_signature="apps.a:f1",
            file_path="a.py",
            mapping_type="manual",
            confidence=0.9,
        )
        TestCaseCodeMapping.objects.create(
            testcase=tc,
            function_signature="apps.a:f2",
            file_path="a.py",
            mapping_type="auto_static",
            confidence=0.6,
        )
        extractor = FeatureExtractor()
        f = extractor.extract(tc)
        assert f.coverage_confidence == 0.9  # 取最高


# ---------------------------------------------------------------------------
# RiskPredictor (编排器)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRiskPredictor:
    def _build_basic(self):
        from apps.precision_testing.models import (
            RepoBinding,
            CodeChangeAnalysis,
            ImpactAnalysis,
        )
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        user = User.objects.create_user(username=f"rp_{timezone.now().timestamp()}")
        project = Project.objects.create(name="RPP", owner=user)
        binding = RepoBinding.objects.create(project=project, repo_path="/tmp/x")
        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding, base_commit="a" * 40, head_commit="b" * 40
        )
        impact = ImpactAnalysis.objects.create(change_analysis=analysis)
        tc = TestCase.objects.create(
            project=project, title="t1", expected_result="ok", author=user, priority="high"
        )
        impact.impacted_testcases = [tc.id]
        impact.save()
        return impact, [tc]

    def test_predict_one_returns_result(self) -> None:
        impact, cases = self._build_basic()
        predictor = RiskPredictor()
        result = predictor.predict_one(cases[0])
        assert isinstance(result, PredictionResult)
        assert 0.0 <= result.risk_score <= 1.0
        assert result.risk_level in {"low", "medium", "high", "critical"}
        assert result.testcase_id == cases[0].id
        assert "failure_rate" in result.features

    def test_predict_batch_consistency(self) -> None:
        impact, cases = self._build_basic()
        predictor = RiskPredictor()
        batch = predictor.predict_batch(cases)
        single = predictor.predict_one(cases[0])
        assert batch[0].risk_score == single.risk_score

    def test_predict_batch_empty(self) -> None:
        predictor = RiskPredictor()
        assert predictor.predict_batch([]) == []

    def test_persist_writes_records(self) -> None:
        from apps.precision_testing.models import RiskPredictionRecord

        impact, cases = self._build_basic()
        predictor = RiskPredictor()
        results = predictor.predict_batch(cases)
        written = predictor.persist(impact, results)
        assert written == len(results)
        assert RiskPredictionRecord.objects.filter(impact_analysis=impact).count() == len(results)

    def test_default_scorer_is_heuristic_when_config_missing(self) -> None:
        predictor = RiskPredictor()
        # 默认配置应使用 heuristic
        assert predictor.scorer.version.startswith("heuristic-")

    def test_explicit_scorer_override(self) -> None:
        custom = HeuristicScorer(weights={"failure_rate": 1.0})
        predictor = RiskPredictor(scorer=custom)
        assert predictor.scorer is custom

    def test_default_scorer_xgboost_when_configured(self) -> None:
        with patch("apps.precision_testing.risk_predictor.settings") as mock_settings:
            mock_settings.PRECISION_TESTING = {"risk_prediction_model": "xgboost"}
            scorer = RiskPredictor._default_scorer()
            assert scorer.version.startswith("xgboost-")


# ---------------------------------------------------------------------------
# 集成场景:critical 用例预测分数明显高于 low
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRiskPredictorIntegration:
    def test_critical_priority_higher_than_low(self) -> None:
        from apps.projects.models import Project
        from apps.testcases.models import TestCase

        user = User.objects.create_user(username=f"int_{timezone.now().timestamp()}")
        project = Project.objects.create(name="IntP", owner=user)
        crit = TestCase.objects.create(
            project=project, title="c", expected_result="ok", author=user, priority="critical"
        )
        low = TestCase.objects.create(
            project=project, title="l", expected_result="ok", author=user, priority="low"
        )
        predictor = RiskPredictor()
        crit_r = predictor.predict_one(crit)
        low_r = predictor.predict_one(low)
        assert crit_r.risk_score > low_r.risk_score


# ---------------------------------------------------------------------------
# 性能基准 — Week 4 §8.5.6 验收指标:1000 用例批量推理 < 3s
# ---------------------------------------------------------------------------


@pytest.mark.perf
class TestHeuristicScorerPerf:
    """启发式打分器的纯推理性能基准。

    覆盖目标:
        * 1000 个 FeatureVector 批量打分应在 3 秒内完成 (§8.5.6)。
        * 单条平均耗时应远低于 100ms 的 P95 预算 (§8.5.6)。

    设计:
        * 直接构造 1000 个 FeatureVector,跳过 ORM 与图谱查询,
          专门衡量 HeuristicScorer.predict_batch 的纯算子开销。
    """

    BATCH_SIZE = 1000
    MAX_TOTAL_SECONDS = 3.0
    MAX_AVG_MS = 100.0

    def _build_features(self, n: int) -> list[FeatureVector]:
        # 构造覆盖各维度的多样特征,避免编译器/CPU 缓存优化导致虚假快路径
        out: list[FeatureVector] = []
        for i in range(n):
            out.append(
                FeatureVector(
                    failure_rate=(i % 11) / 10.0,
                    recent_failure_streak=(i % 5) / 5.0,
                    coverage_confidence=((i * 3) % 11) / 10.0,
                    change_intensity=((i * 7) % 11) / 10.0,
                    priority_score=((i % 4) + 1) / 4.0,
                    days_since_last_change=((i * 13) % 11) / 10.0,
                    has_code_mapping=float(i % 2),
                    testcase_age_days=((i * 17) % 11) / 10.0,
                    impact_path_depth=((i * 19) % 11) / 10.0,
                )
            )
        return out

    def test_predict_batch_1000_under_3s(self) -> None:
        import time

        scorer = HeuristicScorer()
        features = self._build_features(self.BATCH_SIZE)

        start = time.perf_counter()
        scores = scorer.predict_batch(features)
        elapsed = time.perf_counter() - start

        # 正确性: 输出长度 + 取值范围
        assert len(scores) == self.BATCH_SIZE
        assert all(0.0 <= s <= 1.0 for s in scores)

        # 性能预算 (§8.5.6)
        avg_ms = (elapsed / self.BATCH_SIZE) * 1000.0
        assert elapsed < self.MAX_TOTAL_SECONDS, (
            f"1000 用例批量推理耗时 {elapsed:.3f}s,超过 {self.MAX_TOTAL_SECONDS}s 预算"
        )
        assert avg_ms < self.MAX_AVG_MS, (
            f"单条平均耗时 {avg_ms:.3f}ms,超过 {self.MAX_AVG_MS}ms 预算"
        )

        # 客观数字记录到 stdout,便于在 CI/汇报中直接引用
        print(
            f"\n[Week4 perf] HeuristicScorer.predict_batch "
            f"n={self.BATCH_SIZE} total={elapsed*1000:.2f}ms avg={avg_ms:.4f}ms"
        )
