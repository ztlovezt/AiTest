"""精准测试模块 DRF 视图集与 API 视图"""
import logging
from django.db import transaction
from django.db.models import Max
from django.db.models.functions import Coalesce
from django_q.tasks import async_task
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    RepoBinding,
    CodeChangeAnalysis,
    TestCaseCodeMapping,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
)
from .serializers import (
    RepoBindingSerializer,
    CodeChangeAnalysisSerializer,
    TestCaseCodeMappingSerializer,
    TestCaseCodeMappingBulkSerializer,
    TestCaseCodeMappingCsvImportSerializer,
    ImpactAnalysisSerializer,
    RiskPredictionRecordSerializer,
    PrecisionRunRecordSerializer,
)
from .filters import PrecisionRunRecordFilter

logger = logging.getLogger(__name__)


class RepoBindingViewSet(viewsets.ModelViewSet):
    """仓库绑定配置"""
    queryset = RepoBinding.objects.all().select_related('project')
    serializer_class = RepoBindingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """触发代码变更分析

        关键：必须用 transaction.on_commit() 包裹 async_task() 调用。
        否则 worker 可能在 0.1s 内消费任务，但 CodeChangeAnalysis 行所在事务尚未提交，
        worker 端 CodeChangeAnalysis.objects.get(id=...) 会抛 DoesNotExist。
        """
        binding = self.get_object()
        base_commit = request.data.get('base_commit', 'HEAD~1')
        head_commit = request.data.get('head_commit', 'HEAD')

        with transaction.atomic():
            analysis = CodeChangeAnalysis.objects.create(
                repo_binding=binding,
                base_commit=base_commit,
                head_commit=head_commit,
                status='pending',
            )
            analysis_pk = analysis.id

            def _enqueue() -> None:
                task_id = async_task(
                    'apps.precision_testing.tasks.analyze_code_change_task',
                    analysis_pk,
                )
                CodeChangeAnalysis.objects.filter(pk=analysis_pk).update(task_id=task_id)
                logger.info('CodeChangeAnalysis %s enqueued task_id=%s', analysis_pk, task_id)

            transaction.on_commit(_enqueue)

        return Response(
            {'analysis_id': analysis.id, 'task_id': '', 'status': 'pending'},
            status=status.HTTP_202_ACCEPTED,
        )


class CodeChangeAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """代码变更分析记录(只读)"""
    queryset = CodeChangeAnalysis.objects.all().select_related('repo_binding__project')
    serializer_class = CodeChangeAnalysisSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """轮询进度"""
        analysis = self.get_object()
        return Response({
            'id': analysis.id,
            'status': analysis.status,
            'progress': analysis.progress,
            'error_message': analysis.error_message,
        })


class TestCaseCodeMappingViewSet(viewsets.ModelViewSet):
    """用例-代码关联管理"""
    queryset = TestCaseCodeMapping.objects.all().select_related('testcase', 'created_by')
    serializer_class = TestCaseCodeMappingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def auto_build(self, request):
        """触发静态分析自动建图"""
        repo_binding_id = request.data.get('repo_binding_id')
        if not repo_binding_id:
            return Response(
                {'error': 'repo_binding_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task_id = async_task(
            'apps.precision_testing.tasks.build_graph_task',
            repo_binding_id,
        )
        return Response(
            {'task_id': task_id, 'status': 'pending'},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Phase 1 手工标注 — 批量创建/更新映射(单次 ≤ 500 条)。"""
        payload = request.data
        if isinstance(payload, list):
            payload = {"mappings": payload}
        serializer = TestCaseCodeMappingBulkSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='import-csv')
    def import_csv(self, request):
        """CSV 批量导入(multipart 上传或 rows JSON)。

        CSV Schema(5 列):
            testcase_id, function_signature, file_path, mapping_type, confidence

        返回:
            {"created": int, "updated": int, "total": int, "errors": [...]}
        """
        serializer = TestCaseCodeMappingCsvImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        http_status = (
            status.HTTP_207_MULTI_STATUS if result["errors"] else status.HTTP_201_CREATED
        )
        return Response(result, status=http_status)


class ImpactAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """影响分析结果(只读)"""
    queryset = ImpactAnalysis.objects.all().select_related('change_analysis__repo_binding__project')
    serializer_class = ImpactAnalysisSerializer
    permission_classes = [IsAuthenticated]


class RiskPredictionRecordViewSet(viewsets.ModelViewSet):
    """失效概率预测记录"""
    queryset = RiskPredictionRecord.objects.all().select_related('testcase', 'impact_analysis')
    serializer_class = RiskPredictionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['risk_level']

    @action(detail=False, methods=['post'])
    def trigger(self, request):
        """手动触发风险预测"""
        impact_analysis_id = request.data.get('impact_analysis_id')
        if not impact_analysis_id:
            return Response(
                {'error': 'impact_analysis_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task_id = async_task(
            'apps.precision_testing.tasks.predict_risk_task',
            impact_analysis_id,
        )
        return Response(
            {'task_id': task_id, 'status': 'pending'},
            status=status.HTTP_202_ACCEPTED,
        )


class PrecisionRunRecordViewSet(viewsets.ModelViewSet):
    """精准回归执行记录"""
    queryset = PrecisionRunRecord.objects.all().select_related(
        'impact_analysis__change_analysis__repo_binding__project',
        'run_plan'
    )
    serializer_class = PrecisionRunRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PrecisionRunRecordFilter

    def perform_create(self, serializer):
        with transaction.atomic():
            run = serializer.save(status='pending')
            task_id = async_task(
                'apps.precision_testing.tasks.run_precision_regression_task',
                run.id,
            )
            run.task_id = task_id
            run.save(update_fields=['task_id'])

    @action(detail=False, methods=['post'], url_path='trigger-pipeline')
    def trigger_pipeline(self, request):
        """触发端到端精准测试流水线 — Week 4 里程碑入口。

        Body::

            {
                "repo_binding_id": 1,
                "base_commit": "abc123",
                "head_commit": "def456",
                "time_budget_seconds": 900,    # 可选
                "force_full": false,            # 可选
                "force_full_reason": "..."     # force_full=true 时必填
            }
        """
        repo_binding_id = request.data.get('repo_binding_id')
        base_commit = request.data.get('base_commit')
        head_commit = request.data.get('head_commit')
        if not all([repo_binding_id, base_commit, head_commit]):
            return Response(
                {'error': 'repo_binding_id, base_commit, head_commit 必填'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        force_full = bool(request.data.get('force_full', False))
        reason = request.data.get('force_full_reason', '')
        if force_full and not reason:
            return Response(
                {'error': 'force_full=true 时必须提供 force_full_reason'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task_id = async_task(
            'apps.precision_testing.tasks.run_precision_pipeline_task',
            int(repo_binding_id),
            str(base_commit),
            str(head_commit),
            request.data.get('time_budget_seconds'),
            force_full,
            reason,
        )
        return Response(
            {'task_id': task_id, 'status': 'pending'},
            status=status.HTTP_202_ACCEPTED,
        )


class GraphDataView(APIView):
    """获取 Neo4j 图数据 (Cytoscape.js 兼容格式)。

    支持两种模式：
    - 概览（默认）: 全图采样切片，按 ``node_type`` 过滤
    - 子图: 传入 ``center`` + ``label`` 拉取以指定节点为中心的 N 层邻域
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from neo4j.exceptions import ServiceUnavailable
        from .impact_query import get_impact_query

        node_type = request.query_params.get('node_type') or None
        center = request.query_params.get('center') or None
        center_label = request.query_params.get('label', 'Function')
        try:
            limit = max(1, min(int(request.query_params.get('limit', 200)), 1000))
            depth = max(1, min(int(request.query_params.get('depth', 2)), 8))
        except ValueError:
            return Response(
                {'error': 'limit/depth must be integers'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        impact_query = get_impact_query()
        try:
            if center:
                payload = impact_query.query_subgraph(
                    node_id=center,
                    node_label=center_label,
                    depth=depth,
                    node_limit=limit,
                )
            else:
                payload = impact_query.query_overview(
                    node_type=node_type,
                    limit=limit,
                )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceUnavailable:
            logger.warning("Neo4j unavailable, returning empty graph data")
            return Response({'nodes': [], 'edges': []})
        except Exception as exc:
            logger.error("Graph API error: %s", exc)
            return Response({'nodes': [], 'edges': []})

        return Response(payload)


class ImpactQueryView(APIView):
    """影响传播查询 — 给定变更函数，返回受影响函数/用例/接口集合。

    POST body::

        {
            "changed_functions": ["apps.foo.bar:baz", ...],
            "depth": 3,                   # 可选，默认 3，最大 8
            "include_paths": false        # 可选，是否返回传播路径用于前端高亮
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from neo4j.exceptions import ServiceUnavailable
        from .impact_query import get_impact_query

        changed = request.data.get('changed_functions') or []
        if not isinstance(changed, list) or not all(isinstance(x, str) for x in changed):
            return Response(
                {'error': 'changed_functions must be a list[str]'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not changed:
            return Response(
                {'error': 'changed_functions is required and cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            depth = int(request.data.get('depth', 3))
        except (TypeError, ValueError):
            return Response(
                {'error': 'depth must be an integer'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        include_paths = bool(request.data.get('include_paths', False))

        try:
            result = get_impact_query().query_impact(
                changed_function_ids=changed,
                depth=depth,
                include_paths=include_paths,
            )
        except ServiceUnavailable:
            logger.warning("Neo4j unavailable, returning empty impact result")
            return Response({
                'changed_functions': changed,
                'impacted_functions': [],
                'impacted_testcases': [],
                'impacted_endpoints': [],
                'depth': depth,
                'elapsed_ms': 0.0,
                'propagation_paths': [],
                'neo4j_available': False,
            })

        return Response(result.to_dict())


class DashboardView(APIView):
    """精准测试看板汇总数据"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Avg
        from django.utils import timezone
        from datetime import timedelta

        # ── summary ──
        repo_count = RepoBinding.objects.count()
        analysis_count = CodeChangeAnalysis.objects.count()
        mapping_count = TestCaseCodeMapping.objects.count()
        avg_reduction = (
            PrecisionRunRecord.objects.filter(status='completed')
            .aggregate(avg=Avg('reduction_rate'))['avg']
            or 0.0
        )

        # ── risk_distribution ──
        risk_distribution = dict(
            RiskPredictionRecord.objects.values('risk_level')
            .annotate(count=Count('id'))
            .values_list('risk_level', 'count')
        )
        for level in ['high', 'medium', 'low']:
            risk_distribution.setdefault(level, 0)

        # ── trend: last 14 days ──
        today = timezone.now().date()
        dates = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        trend = {'dates': dates, 'analysis_counts': [], 'function_counts': []}
        for d in dates:
            day_start = timezone.make_aware(
                timezone.datetime.combine(
                    timezone.datetime.strptime(d, '%Y-%m-%d').date(),
                    timezone.datetime.min.time(),
                )
            )
            day_end = day_start + timedelta(days=1)
            day_analyses = CodeChangeAnalysis.objects.filter(
                created_at__gte=day_start, created_at__lt=day_end
            )
            trend['analysis_counts'].append(day_analyses.count())
            func_count = sum(
                len(a.changed_functions or []) for a in day_analyses
            )
            trend['function_counts'].append(func_count)

        # ── top_risky_files ──
        top_risky_files = []
        try:
            recent_predictions = (
                RiskPredictionRecord.objects.select_related(
                    'impact_analysis__change_analysis'
                )
                .order_by('-risk_score')[:10]
            )
            for pred in recent_predictions:
                ca = pred.impact_analysis.change_analysis
                files = ca.changed_files or []
                for f in files[:3]:
                    fp = (
                        f.get('file_path', f)
                        if isinstance(f, dict)
                        else str(f)
                    )
                    top_risky_files.append({
                        'file_path': fp,
                        'risk_score': pred.risk_score,
                        'change_count': len(ca.changed_functions or []),
                    })
        except Exception as exc:
            logger.warning('top_risky_files query failed: %s', exc)

        # Deduplicate by file_path
        seen = set()
        unique_top = []
        for item in top_risky_files:
            fp = item['file_path']
            if fp and fp not in seen:
                seen.add(fp)
                unique_top.append(item)
        top_risky_files = unique_top[:10]

        # ── run_stats: last 14 days ──
        run_stats = {'dates': dates, 'precision_counts': [], 'full_counts': []}
        for d in dates:
            day_start = timezone.make_aware(
                timezone.datetime.combine(
                    timezone.datetime.strptime(d, '%Y-%m-%d').date(),
                    timezone.datetime.min.time(),
                )
            )
            day_end = day_start + timedelta(days=1)
            precision_runs = PrecisionRunRecord.objects.filter(
                status='completed', created_at__gte=day_start, created_at__lt=day_end
            )
            run_stats['precision_counts'].append(precision_runs.count())
            # Full-run count is not tracked separately in MVP; use 0 as placeholder
            run_stats['full_counts'].append(0)

        return Response({
            'summary': {
                'repo_count': repo_count,
                'analysis_count': analysis_count,
                'mapping_count': mapping_count,
                'avg_reduction_rate': round(avg_reduction, 3),
            },
            'risk_distribution': risk_distribution,
            'trend': trend,
            'top_risky_files': top_risky_files,
            'run_stats': run_stats,
        })


class GitWebhookView(APIView):
    """接收 Git push webhook,自动触发分析"""
    permission_classes = []  # Webhook 通常使用签名验证而非 JWT

    def post(self, request):
        # MVP: 简化处理,实际生产需验证签名
        repo_binding_id = request.data.get('repo_binding_id')
        base_commit = request.data.get('before')
        head_commit = request.data.get('after')

        if not all([repo_binding_id, base_commit, head_commit]):
            return Response(
                {'error': 'repo_binding_id, before, after are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            binding = RepoBinding.objects.get(id=repo_binding_id, is_active=True)
        except RepoBinding.DoesNotExist:
            return Response(
                {'error': 'RepoBinding not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        analysis = CodeChangeAnalysis.objects.create(
            repo_binding=binding,
            base_commit=base_commit,
            head_commit=head_commit,
            status='pending',
        )
        task_id = async_task(
            'apps.precision_testing.tasks.analyze_code_change_task',
            analysis.id,
        )
        analysis.task_id = task_id
        analysis.save(update_fields=['task_id'])

        return Response(
            {'analysis_id': analysis.id, 'task_id': task_id},
            status=status.HTTP_202_ACCEPTED,
        )


class CoverageGateView(APIView):
    """增量覆盖率门禁"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        analysis_id = request.data.get('analysis_id')
        threshold = request.data.get('threshold', 0.80)

        if not analysis_id:
            return Response(
                {'error': 'analysis_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            analysis = CodeChangeAnalysis.objects.get(id=analysis_id)
        except CodeChangeAnalysis.DoesNotExist:
            return Response(
                {'error': 'Analysis not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # MVP: 简化门禁逻辑,实际需读取 coverage.json 计算
        impacted_count = len(analysis.changed_functions)
        passed = impacted_count <= 5  # 占位逻辑

        return Response({
            'analysis_id': analysis_id,
            'passed': passed,
            'threshold': threshold,
            'impacted_functions': impacted_count,
        })
