"""精准测试模块 Django-Q 后台任务"""
import logging
import os
from pathlib import Path

from django.utils import timezone
from django_q.tasks import async_task

from .models import (
    CodeChangeAnalysis,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
    TestCaseCodeMapping,
)

logger = logging.getLogger(__name__)


def analyze_code_change_task(analysis_id: int) -> None:
    """代码变更分析: git diff → AST → 变更函数列表 → 写入 CodeChangeAnalysis

    步骤:
        1. 读取 RepoBinding 获取仓库路径
        2. GitPython 获取 base..head diff
        3. unidiff 解析变更文件和行号
        4. AST 解析变更文件,定位受影响函数
        5. (可选) Coverage.py 数据 → 自动建立 TestCaseCodeMapping (auto_static)
        6. Neo4j 查询 TESTED_BY 关系,获取受影响用例
        7. 创建 ImpactAnalysis 记录
    """
    analysis = CodeChangeAnalysis.objects.get(id=analysis_id)
    analysis.status = 'running'
    analysis.progress = 10
    analysis.started_at = timezone.now()
    analysis.save(update_fields=['status', 'progress', 'started_at'])

    try:
        repo_path = analysis.repo_binding.repo_path
        base_commit = analysis.base_commit
        head_commit = analysis.head_commit

        # Step 1: Git diff
        from .git_analyzer import GitDiffAnalyzer
        git_analyzer = GitDiffAnalyzer(repo_path)
        diff_result = git_analyzer.get_diff(base_commit, head_commit)
        analysis.changed_files = diff_result.get('changed_files', [])
        analysis.progress = 30
        analysis.save(update_fields=['changed_files', 'progress'])

        # Step 2: AST 解析变更函数
        from .ast_analyzer import ASTAnalyzer
        ast_analyzer = ASTAnalyzer(repo_path)
        changed_functions = ast_analyzer.get_changed_functions(diff_result)
        analysis.changed_functions = changed_functions
        analysis.progress = 50
        analysis.save(update_fields=['changed_functions', 'progress'])

        # Step 3: 自动 TestCaseCodeMapping(Phase 2 静态分析)
        _build_auto_static_mappings(analysis.repo_binding, repo_path)
        analysis.progress = 60
        analysis.save(update_fields=['progress'])

        # Step 4: Neo4j 查询受影响用例
        from .neo4j_client import get_neo4j_client
        client = get_neo4j_client()
        function_ids = [f['signature'] for f in changed_functions]
        impacted_functions = client.get_impacted_functions(function_ids)
        impacted_testcases = client.get_tested_by(impacted_functions)

        # Step 5: 创建 ImpactAnalysis
        ImpactAnalysis.objects.create(
            change_analysis=analysis,
            impacted_functions=impacted_functions,
            impacted_testcases=impacted_testcases,
            status='completed',
        )

        analysis.status = 'completed'
        analysis.progress = 100
        analysis.completed_at = timezone.now()
        analysis.save(update_fields=['status', 'progress', 'completed_at'])
        logger.info("CodeChangeAnalysis %s completed", analysis_id)

    except Exception as exc:
        logger.exception("CodeChangeAnalysis %s failed: %s", analysis_id, exc)
        analysis.status = 'failed'
        analysis.error_message = str(exc)
        analysis.completed_at = timezone.now()
        analysis.save(update_fields=['status', 'error_message', 'completed_at'])
        raise


def _build_auto_static_mappings(repo_binding, repo_path: str) -> int:
    """若仓库内存在 ``.coverage`` 数据库,则自动登记 ``auto_static`` 类型的
    :class:`TestCaseCodeMapping`。

    Returns:
        新创建的映射条数(已存在则跳过)。
    """
    from .coverage_service import CoverageService
    from apps.testcases.models import TestCase

    coverage_db = Path(repo_path) / ".coverage"
    if not coverage_db.exists():
        logger.debug("跳过 auto_static 映射: 未发现 .coverage (%s)", coverage_db)
        return 0

    try:
        service = CoverageService(repo_path=repo_path, coverage_db=coverage_db)
        candidates = service.build_static_mappings()
    except Exception as exc:  # pragma: no cover - 防御
        logger.warning("CoverageService 解析失败,跳过 auto_static: %s", exc)
        return 0

    created = 0
    project = repo_binding.project
    testcase_qs = TestCase.objects.filter(project=project).only("id", "title")
    title_to_id = {tc.title: tc.id for tc in testcase_qs}

    for candidate in candidates:
        # test_id 形如 ``tests/api/test_users.py::test_create_user``
        node_name = candidate["test_id"].rsplit("::", 1)[-1]
        tc_id = title_to_id.get(node_name)
        if tc_id is None:
            continue
        _, was_created = TestCaseCodeMapping.objects.update_or_create(
            testcase_id=tc_id,
            function_signature=candidate["function_signature"],
            defaults={
                "file_path": candidate["file_path"],
                "mapping_type": candidate["mapping_type"],
                "confidence": candidate["confidence"],
            },
        )
        if was_created:
            created += 1
    logger.info("auto_static 映射创建数: %d (来自 %d 个候选)", created, len(candidates))
    return created


def build_graph_task(repo_binding_id: int) -> None:
    """全量图谱构建: AST 遍历 + Neo4j batch write

    遍历项目所有 Python 文件,提取 Function/Class/APIEndpoint 节点,
    并建立 CALLS/TESTED_BY 关系。
    """
    from .models import RepoBinding
    from .graph_builder import GraphBuilder

    binding = RepoBinding.objects.get(id=repo_binding_id)
    builder = GraphBuilder(binding.repo_path)
    builder.build_full_graph()
    logger.info("Graph built for repo %s", binding.repo_path)


def predict_risk_task(impact_analysis_id: int) -> None:
    """失效概率预测: 特征提取 → XGBoost 推理 → 写入 RiskPredictionRecord

    冷启动策略: 若历史数据不足 50 条,则使用启发式规则(修改频率+历史失败率)
    替代模型预测。
    """
    from .risk_predictor import RiskPredictor

    impact = ImpactAnalysis.objects.get(id=impact_analysis_id)
    predictor = RiskPredictor()

    for testcase_id in impact.impacted_testcases:
        try:
            testcase = impact.change_analysis.repo_binding.project.testcases.get(id=testcase_id)
        except Exception:
            continue

        # 冷启动: 启发式规则
        features = predictor.extract_features(testcase)
        risk_score = predictor.predict_heuristic(features)

        RiskPredictionRecord.objects.create(
            testcase=testcase,
            impact_analysis=impact,
            risk_score=risk_score,
            risk_level=predictor.score_to_level(risk_score),
            features=features,
            model_version='heuristic-v1',
        )

    logger.info("Risk prediction completed for impact analysis %s", impact_analysis_id)


def run_precision_regression_task(precision_run_id: int) -> None:
    """执行精准回归: 生成最小回归集 → 创建 TestPlan + TestRun → 调度执行"""
    from .regression_selector import RegressionSelector

    run = PrecisionRunRecord.objects.get(id=precision_run_id)
    run.status = 'running'
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at'])

    try:
        impact = run.impact_analysis
        selector = RegressionSelector(impact)
        selected, reduction_rate = selector.select()

        run.selected_testcases = selected
        run.reduction_rate = reduction_rate
        run.progress = 50
        run.save(update_fields=['selected_testcases', 'reduction_rate', 'progress'])

        # 创建 TestPlan + TestRun
        from apps.executions.models import TestPlan, TestRun
        plan = TestPlan.objects.create(
            name=f"精准回归 #{precision_run_id}",
            creator_id=1,  # 占位,实际应从 run 获取
        )
        plan.projects.add(impact.change_analysis.repo_binding.project)

        test_run = TestRun.objects.create(
            name=f"精准回归执行 #{precision_run_id}",
            test_plan=plan,
            project=impact.change_analysis.repo_binding.project,
            assignee_id=1,
            creator_id=1,
            status='untested',
        )
        # 关联选中的用例
        from apps.testcases.models import TestCase
        for tc_id in selected:
            try:
                tc = TestCase.objects.get(id=tc_id)
                test_run.testcases.add(tc)
            except TestCase.DoesNotExist:
                pass

        run.run_plan = plan
        run.status = 'completed'
        run.progress = 100
        run.completed_at = timezone.now()
        run.save(update_fields=['run_plan', 'status', 'progress', 'completed_at'])
        logger.info("PrecisionRun %s completed", precision_run_id)

    except Exception as exc:
        logger.exception("PrecisionRun %s failed: %s", precision_run_id, exc)
        run.status = 'failed'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        raise
