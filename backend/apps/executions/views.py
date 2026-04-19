from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import TestPlan, TestRun, TestRunCase, TestRunCaseHistory
from apps.testcases.models import TestCase
from apps.projects.models import Project
from .serializers import (TestPlanSerializer, TestRunSerializer, TestRunCaseSerializer,
                         TestPlanDetailSerializer, TestRunCaseDetailSerializer,
                         TestRunCaseHistorySerializer)

class TestPlanViewSet(viewsets.ModelViewSet):
    """
    测试计划视图集
    """
    queryset = TestPlan.objects.all().order_by('-created_at')
    serializer_class = TestPlanSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestPlanDetailSerializer
        return TestPlanSerializer

    def perform_create(self, serializer):
        # 在创建TestPlan时，设置creator并自动为每个项目创建TestRun和TestRunCase
        # 获取版本信息
        version_id = self.request.data.get('version')
        version = None
        if version_id:
            from apps.versions.models import Version
            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                pass
        
        test_plan = serializer.save(creator=self.request.user, version=version)
        
        # 获取选中的项目和测试用例
        project_ids = self.request.data.get('projects', [])
        testcase_ids = self.request.data.get('testcases', [])
        
        if project_ids:
            # 设置测试计划的项目关联
            test_plan.projects.set(project_ids)
            
            # 为每个项目创建TestRun
            for project_id in project_ids:
                try:
                    project = Project.objects.get(id=project_id)
                    test_run = TestRun.objects.create(
                        name=f"{test_plan.name} - {project.name} Execution",
                        test_plan=test_plan,
                        project=project,
                        version=test_plan.version,
                        creator=test_plan.creator,
                        assignee=test_plan.creator  # 默认指派给自己
                    )
                    
                    # 为TestRun关联测试用例
                    if testcase_ids:
                        test_run_cases = []
                        for case_id in testcase_ids:
                            try:
                                testcase = TestCase.objects.get(id=case_id)
                                test_run_cases.append(
                                    TestRunCase(test_run=test_run, testcase=testcase)
                                )
                            except TestCase.DoesNotExist:
                                continue
                        TestRunCase.objects.bulk_create(test_run_cases)
                        test_run.testcases.set(testcase_ids)
                        
                except Project.DoesNotExist:
                    continue

    @action(detail=False, methods=['get'])
    def testcases_by_projects(self, request):
        """
        根据项目获取测试用例（支持分页和筛选）
        """
        project_ids = request.query_params.getlist('project_ids')
        if not project_ids:
            return Response({
                'error': '请先选择项目',
                'detail': '请先选择项目后再选择测试用例'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 过滤数字字符串和空值
            project_ids = [int(pid) for pid in project_ids if pid and pid.isdigit()]

            if not project_ids:
                return Response({
                    'error': '无效的项目 ID',
                    'detail': '请选择有效的项目'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取指定项目的测试用例
            queryset = TestCase.objects.filter(
                project_id__in=project_ids,
                status__in=['draft', 'active']  # 包含草稿和激活状态的测试用例
            ).order_by('id')  # 正序排列

            # 关键词搜索（标题）
            keyword = request.query_params.get('keyword')
            if keyword:
                queryset = queryset.filter(title__icontains=keyword)

            # 优先级筛选
            priority = request.query_params.get('priority')
            if priority:
                queryset = queryset.filter(priority=priority)

            # 测试类型筛选
            test_type = request.query_params.get('test_type')
            if test_type:
                queryset = queryset.filter(test_type=test_type)

            # 支持通过 ids 参数获取特定用例（用于回显已选用例）
            ids_param = request.query_params.get('ids')
            if ids_param:
                try:
                    ids = [int(x) for x in ids_param.split(',') if x.strip().isdigit()]
                    if ids:
                        queryset = queryset.filter(id__in=ids)
                except (ValueError, TypeError):
                    pass

            # 分页
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))

            # 获取总数
            total = queryset.count()

            # 分页切片
            start = (page - 1) * page_size
            end = start + page_size
            testcases = queryset[start:end].values(
                'id', 'title', 'priority', 'test_type', 'status', 'project__name'
            )

            return Response({
                'results': list(testcases),
                'count': total
            })

        except ValueError:
            return Response({
                'error': '项目 ID 格式错误',
                'detail': '请提供有效的项目 ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': '获取测试用例失败',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        # 在更新TestPlan时，处理版本信息
        version_id = self.request.data.get('version')
        version = None
        if version_id:
            from apps.versions.models import Version
            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                pass
        
        # 更新测试计划
        test_plan = serializer.save(version=version)
        
        # 更新项目关联
        project_ids = self.request.data.get('projects', [])
        if project_ids:
            test_plan.projects.set(project_ids)
        
        # 更新指派人员
        assignee_ids = self.request.data.get('assignees', [])
        if assignee_ids:
            test_plan.assignees.set(assignee_ids)


class TestRunViewSet(viewsets.ModelViewSet):
    """
    测试执行视图集
    """
    queryset = TestRun.objects.all().order_by('-created_at')
    serializer_class = TestRunSerializer

class TestRunCaseViewSet(viewsets.ModelViewSet):
    """
    测试执行用例视图集
    """
    queryset = TestRunCase.objects.all()
    serializer_class = TestRunCaseSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestRunCaseDetailSerializer
        return TestRunCaseSerializer

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """
        更新单个用例的执行状态，并自动创建历史记录
        """
        run_case = self.get_object()
        new_status = request.data.get('status')
        actual_result = request.data.get('actual_result', '')
        comments = request.data.get('comments', '')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建历史记录
        TestRunCaseHistory.objects.create(
            run_case=run_case,
            status=new_status,
            actual_result=actual_result,
            comments=comments,
            executed_by=request.user,
            executed_at=timezone.now()
        )
        
        # 更新执行用例状态
        run_case.status = new_status
        run_case.actual_result = actual_result
        run_case.comments = comments
        run_case.executed_by = request.user
        run_case.executed_at = timezone.now()
        run_case.save()
        
        return Response(TestRunCaseDetailSerializer(run_case).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        获取用例执行历史记录
        """
        run_case = self.get_object()
        history = run_case.history.all().order_by('-executed_at')
        serializer = TestRunCaseHistorySerializer(history, many=True)
        return Response(serializer.data)

class TestRunCaseHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    测试执行历史视图集（只读）
    """
    queryset = TestRunCaseHistory.objects.all().order_by('-executed_at')
    serializer_class = TestRunCaseHistorySerializer
