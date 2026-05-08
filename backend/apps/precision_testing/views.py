"""精准测试模块 DRF 视图集与 API 视图"""
import logging
from django.db import transaction
from django_q.tasks import async_task
from rest_framework import viewsets, status
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
    ImpactAnalysisSerializer,
    RiskPredictionRecordSerializer,
    PrecisionRunRecordSerializer,
)

logger = logging.getLogger(__name__)


class RepoBindingViewSet(viewsets.ModelViewSet):
    """仓库绑定配置"""
    queryset = RepoBinding.objects.all().select_related('project')
    serializer_class = RepoBindingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """触发代码变更分析"""
        binding = self.get_object()
        base_commit = request.data.get('base_commit', 'HEAD~1')
        head_commit = request.data.get('head_commit', 'HEAD')

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
            {'analysis_id': analysis.id, 'task_id': task_id, 'status': 'pending'},
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
    queryset = PrecisionRunRecord.objects.all().select_related('impact_analysis__change_analysis', 'run_plan')
    serializer_class = PrecisionRunRecordSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        with transaction.atomic():
            run = serializer.save(status='pending')
            task_id = async_task(
                'apps.precision_testing.tasks.run_precision_regression_task',
                run.id,
            )
            run.task_id = task_id
            run.save(update_fields=['task_id'])


class GraphDataView(APIView):
    """获取 Neo4j 图数据(ECharts 格式)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .neo4j_client import get_neo4j_client

        node_type = request.query_params.get('node_type', '')
        limit = int(request.query_params.get('limit', 200))

        client = get_neo4j_client()
        nodes_query = (
            "MATCH (n) "
            "RETURN id(n) AS node_id, labels(n)[0] AS label, "
            "       n.id AS id, n.name AS name, n.title AS title "
            "LIMIT $limit"
        )
        rels_query = (
            "MATCH (a)-[r]->(b) "
            "RETURN id(a) AS source, id(b) AS target, type(r) AS rel_type "
            "LIMIT $limit"
        )

        node_records = client.execute_read(nodes_query, {'limit': limit})
        rel_records = client.execute_read(rels_query, {'limit': limit})

        nodes = []
        for r in node_records:
            label = r.get('label', 'Unknown')
            name = r.get('name') or r.get('title') or r.get('id', '')
            nodes.append({
                'id': str(r['node_id']),
                'name': name,
                'category': label,
                'label': label,
            })

        links = []
        for r in rel_records:
            links.append({
                'source': str(r['source']),
                'target': str(r['target']),
                'relation': r['rel_type'],
            })

        return Response({'nodes': nodes, 'links': links})


class DashboardView(APIView):
    """精准测试看板汇总数据"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Avg

        total_mappings = TestCaseCodeMapping.objects.count()
        total_analyses = CodeChangeAnalysis.objects.count()
        completed_analyses = CodeChangeAnalysis.objects.filter(status='completed').count()
        avg_reduction = PrecisionRunRecord.objects.filter(
            status='completed'
        ).aggregate(avg=Avg('reduction_rate'))['avg'] or 0.0

        recent_runs = PrecisionRunRecord.objects.filter(
            status='completed'
        ).order_by('-created_at')[:10].values(
            'id', 'reduction_rate', 'total_testcases',
            'created_at'
        )

        return Response({
            'total_mappings': total_mappings,
            'total_analyses': total_analyses,
            'completed_analyses': completed_analyses,
            'avg_reduction_rate': round(avg_reduction, 3),
            'recent_runs': list(recent_runs),
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
