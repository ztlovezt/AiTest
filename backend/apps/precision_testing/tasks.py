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

    当 pytest nodeid 无法匹配已有 :class:`TestCase` 时,自动创建缺失的
    ``TestCase`` 记录(标题使用 nodeid,项目归属当前仓库绑定项目)。

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

    if not candidates:
        logger.info("Coverage 解析结果为空,无候选映射")
        return 0

    created = 0
    project = repo_binding.project
    testcase_qs = TestCase.objects.filter(project=project).only("id", "title")
    title_to_id = {tc.title: tc.id for tc in testcase_qs}

    # 兜底:若没有任何 TestCase,按 nodeid 自动创建(使用系统用户作为 author)
    default_author_id = _get_default_user_id()

    for candidate in candidates:
        # test_id 形如 ``tests/api/test_users.py::test_create_user``
        node_name = candidate["test_id"].rsplit("::", 1)[-1]
        tc_id = title_to_id.get(node_name)
        if tc_id is None:
            # 未匹配到已有用例,自动创建
            tc = TestCase.objects.create(
                project=project,
                title=node_name,
                expected_result="",
                author_id=default_author_id,
                priority="medium",
                status="draft",
                test_type="functional",
            )
            tc_id = tc.id
            title_to_id[node_name] = tc_id
            logger.debug("自动创建 TestCase: title=%s id=%s", node_name, tc_id)

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
    logger.info("auto_static 映射创建数: %d (来自 %d 个候选,含 %d 个自动创建用例)",
                created, len(candidates), len(title_to_id) - testcase_qs.count())
    return created


def _get_default_user_id() -> int | None:
    """获取系统默认用户 ID,用于自动创建 TestCase 的 author 字段。"""
    try:
        from apps.users.models import User
        user = User.objects.filter(is_superuser=True).first()
        if user:
            return user.id
        user = User.objects.first()
        return user.id if user else None
    except Exception:
        return None


def build_graph_task(repo_binding_id: int) -> dict:
    """全量图谱构建: AST 遍历 + Neo4j batch write + 自动 Coverage 映射提取。

    遍历项目所有 Python 文件,提取 Function/Class/APIEndpoint 节点,
    并建立 CALLS/TESTED_BY 关系。
    若仓库根目录存在 ``.coverage`` 数据库,同时自动创建
    ``auto_static`` 类型的 :class:`TestCaseCodeMapping`。
    """
    from .models import RepoBinding
    from .graph_builder import GraphBuilder

    binding = RepoBinding.objects.get(id=repo_binding_id)
    builder = GraphBuilder(binding.repo_path)
    graph_stats = builder.build_full_graph()

    # 同步从 .coverage 自动提取 TestCaseCodeMapping
    mapping_created = _build_auto_static_mappings(binding, binding.repo_path)
    graph_stats['mapping_created'] = mapping_created

    logger.info(
        "Graph built for repo %s (nodes=%s, mappings_created=%d)",
        binding.repo_path,
        graph_stats.get('node_counts'),
        mapping_created,
    )
    return graph_stats


def predict_risk_task(impact_analysis_id: int) -> int:
    """失效概率预测: 批量特征提取 → 批量推理 → bulk_create RiskPredictionRecord。

    Week 4 升级:
        - 使用 RiskPredictor 批量 API 消除 N+1
        - FeatureExtractor 接收 change_analysis + impact_paths,
          为 9 维特征提供完整上下文
        - 持久化由 RiskPredictor.persist 统一处理

    Returns:
        写入的预测记录条数。
    """
    from apps.testcases.models import TestCase
    from .risk_predictor import FeatureExtractor, RiskPredictor

    impact = ImpactAnalysis.objects.get(id=impact_analysis_id)

    # 清空该 impact 之前的预测,避免重复
    RiskPredictionRecord.objects.filter(impact_analysis=impact).delete()

    impacted_ids = impact.impacted_testcases or []
    if not impacted_ids:
        logger.info("ImpactAnalysis %s 无受影响用例,跳过预测", impact_analysis_id)
        return 0

    project = impact.change_analysis.repo_binding.project
    testcases = list(
        TestCase.objects.filter(project=project, id__in=impacted_ids).prefetch_related(
            "code_mappings"
        )
    )
    if not testcases:
        logger.warning("ImpactAnalysis %s 受影响用例无法查询到任何 TestCase", impact_analysis_id)
        return 0

    # 从 impact.impacted_functions 估算 path depth(简化:有则深度=1,无则=0)
    impact_paths = {tc.id: 1 for tc in testcases}

    extractor = FeatureExtractor(
        change_analysis=impact.change_analysis,
        impact_paths=impact_paths,
    )
    predictor = RiskPredictor(extractor=extractor)
    results = predictor.predict_batch(testcases)
    written = predictor.persist(impact, results)
    logger.info(
        "Risk prediction for impact %s: %d records (model=%s)",
        impact_analysis_id,
        written,
        predictor.scorer.version,
    )
    return written


def run_precision_regression_task(precision_run_id: int) -> dict:
    """执行精准回归: 生成最小回归集 → 创建 TestPlan + TestRun → 调度执行。

    Week 4 升级:
        - 使用 RegressionSelector + SelectionResult 替代旧 tuple 返回
        - 写入完整选集元数据(must_run_count / candidate_count / reason)
        - 失败可重试,中间状态写入 progress 字段
    """
    from .regression_selector import RegressionSelector, persist_selection

    run = PrecisionRunRecord.objects.get(id=precision_run_id)
    run.status = 'running'
    run.started_at = timezone.now()
    run.save(update_fields=['status', 'started_at'])

    try:
        impact = run.impact_analysis
        selector = RegressionSelector(impact)
        result = selector.select()

        run.selected_testcases = result.selected_testcase_ids
        run.total_testcases = result.total_testcases
        run.reduction_rate = result.reduction_rate
        run.progress = 50
        run.save(update_fields=[
            'selected_testcases', 'total_testcases', 'reduction_rate', 'progress',
        ])

        # 同步写回 ImpactAnalysis
        persist_selection(impact, result)

        # 创建 TestPlan + TestRun
        from apps.executions.models import TestPlan, TestRun
        from apps.testcases.models import TestCase

        project = impact.change_analysis.repo_binding.project
        plan = TestPlan.objects.create(
            name=f"精准回归 #{precision_run_id}",
            creator_id=1,
        )
        plan.projects.add(project)

        test_run = TestRun.objects.create(
            name=f"精准回归执行 #{precision_run_id}",
            test_plan=plan,
            project=project,
            assignee_id=1,
            creator_id=1,
            status='untested',
        )
        # 批量绑定用例
        if result.selected_testcase_ids:
            cases = TestCase.objects.filter(id__in=result.selected_testcase_ids)
            test_run.testcases.add(*list(cases))

        run.run_plan = plan
        run.status = 'completed'
        run.progress = 100
        run.completed_at = timezone.now()
        run.save(update_fields=['run_plan', 'status', 'progress', 'completed_at'])
        logger.info(
            "PrecisionRun %s completed: %d/%d (reduction=%.2f)",
            precision_run_id,
            len(result.selected_testcase_ids),
            result.total_testcases,
            result.reduction_rate,
        )
        return result.as_dict()

    except Exception as exc:
        logger.exception("PrecisionRun %s failed: %s", precision_run_id, exc)
        run.status = 'failed'
        run.completed_at = timezone.now()
        run.save(update_fields=['status', 'completed_at'])
        raise


def run_precision_pipeline_task(
    repo_binding_id: int,
    base_commit: str,
    head_commit: str,
    time_budget_seconds: int | None = None,
    force_full: bool = False,
    force_full_reason: str = "",
) -> dict:
    """端到端精准测试流水线 — Week 4 里程碑入口。

    阶段:
        1. 创建 CodeChangeAnalysis (变更分析)
        2. 调用 analyze_code_change_task (Git diff + AST + 影响)
        3. 调用 predict_risk_task (风险预测)
        4. 创建 PrecisionRunRecord + 调用 run_precision_regression_task

    Returns:
        {analysis_id, impact_id, run_id, selection: dict}
    """
    from .models import RepoBinding

    binding = RepoBinding.objects.get(id=repo_binding_id)
    analysis = CodeChangeAnalysis.objects.create(
        repo_binding=binding,
        base_commit=base_commit,
        head_commit=head_commit,
        status='pending',
    )

    # Stage 1+2:变更分析 + 影响分析
    analyze_code_change_task(analysis.id)
    analysis.refresh_from_db()
    if analysis.status != 'completed':
        raise RuntimeError(
            f"analyze_code_change_task 未完成: status={analysis.status} err={analysis.error_message}"
        )

    impact = analysis.impact_results.order_by('-created_at').first()
    if impact is None:
        raise RuntimeError("ImpactAnalysis 未生成")

    # Stage 3:风险预测
    predict_risk_task(impact.id)

    # Stage 4:创建 PrecisionRunRecord + 执行选集
    run = PrecisionRunRecord.objects.create(
        impact_analysis=impact,
        status='pending',
    )
    selection = run_precision_regression_task(run.id)

    return {
        "analysis_id": analysis.id,
        "impact_id": impact.id,
        "run_id": run.id,
        "selection": selection,
    }
