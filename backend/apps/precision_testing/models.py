from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.testcases.models import TestCase
from apps.executions.models import TestPlan, TestRun


class RepoBinding(models.Model):
    """项目与 Git 仓库绑定"""
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='repo_binding',
        verbose_name='关联项目'
    )
    name = models.CharField(max_length=200, blank=True, default='', verbose_name='仓库显示名称')
    repo_path = models.CharField(max_length=500, blank=True, default='', verbose_name='仓库本地路径')
    repo_url = models.CharField(max_length=500, blank=True, default='', verbose_name='仓库远程地址')
    default_branch = models.CharField(max_length=100, default='main', verbose_name='默认分支')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'precision_repo_bindings'
        verbose_name = '仓库绑定'
        verbose_name_plural = '仓库绑定'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.name} -> {self.repo_path}"


class CodeChangeAnalysis(models.Model):
    """代码变更分析任务"""
    STATUS_CHOICES = [
        ('pending', '排队中'),
        ('running', '分析中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    repo_binding = models.ForeignKey(
        RepoBinding, on_delete=models.CASCADE, related_name='analyses',
        verbose_name='关联仓库'
    )
    base_commit = models.CharField(max_length=40, verbose_name='基准 Commit SHA')
    head_commit = models.CharField(max_length=40, verbose_name='当前 Commit SHA')
    changed_files = models.JSONField(default=list, blank=True, verbose_name='变更文件列表')
    changed_functions = models.JSONField(default=list, blank=True, verbose_name='变更函数列表')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='状态'
    )
    task_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='异步任务ID')
    progress = models.IntegerField(default=0, verbose_name='进度(%)')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'precision_change_analyses'
        verbose_name = '代码变更分析'
        verbose_name_plural = '代码变更分析'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.repo_binding.project.name}: {self.base_commit[:7]}..{self.head_commit[:7]}"


class TestCaseCodeMapping(models.Model):
    """测试用例与代码函数关联"""
    MAPPING_TYPE_CHOICES = [
        ('manual', '手工映射'),
        ('auto_static', '静态分析'),
        ('auto_dynamic', '动态学习'),
    ]

    testcase = models.ForeignKey(
        TestCase, on_delete=models.CASCADE, related_name='code_mappings',
        verbose_name='测试用例'
    )
    function_signature = models.CharField(
        max_length=500, verbose_name='函数签名',
        help_text='格式: apps.module.views:ClassName.method_name'
    )
    file_path = models.CharField(max_length=500, verbose_name='文件相对路径')
    mapping_type = models.CharField(
        max_length=20, choices=MAPPING_TYPE_CHOICES, default='manual',
        verbose_name='映射类型'
    )
    confidence = models.FloatField(default=1.0, verbose_name='置信度')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'precision_testcase_mappings'
        verbose_name = '用例代码映射'
        verbose_name_plural = '用例代码映射'
        unique_together = ['testcase', 'function_signature']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.testcase.title} -> {self.function_signature}"


class ImpactAnalysis(models.Model):
    """变更影响分析结果"""
    STATUS_CHOICES = [
        ('pending', '计算中'),
        ('completed', '已完成'),
    ]

    change_analysis = models.ForeignKey(
        CodeChangeAnalysis, on_delete=models.CASCADE, related_name='impact_results',
        verbose_name='关联变更分析'
    )
    impacted_functions = models.JSONField(default=list, blank=True, verbose_name='受影响函数列表')
    impacted_testcases = models.JSONField(default=list, blank=True, verbose_name='受影响用例ID列表')
    min_regression_set = models.JSONField(default=list, blank=True, verbose_name='最小回归集')
    regression_time_estimate = models.IntegerField(default=0, verbose_name='预估回归时间(秒)')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='状态'
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'precision_impact_analyses'
        verbose_name = '影响分析'
        verbose_name_plural = '影响分析'
        ordering = ['-created_at']

    def __str__(self):
        return f"Impact of {self.change_analysis}"


class RiskPredictionRecord(models.Model):
    """失效概率预测记录"""
    RISK_LEVEL_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '极高'),
    ]

    testcase = models.ForeignKey(
        TestCase, on_delete=models.CASCADE, related_name='risk_predictions',
        verbose_name='测试用例'
    )
    impact_analysis = models.ForeignKey(
        ImpactAnalysis, on_delete=models.CASCADE, related_name='risk_records',
        verbose_name='关联影响分析'
    )
    risk_score = models.FloatField(verbose_name='风险分数')
    risk_level = models.CharField(
        max_length=20, choices=RISK_LEVEL_CHOICES, default='low',
        verbose_name='风险等级'
    )
    features = models.JSONField(default=dict, blank=True, verbose_name='特征向量')
    model_version = models.CharField(max_length=50, blank=True, null=True, verbose_name='模型版本')
    predicted_at = models.DateTimeField(default=timezone.now, verbose_name='预测时间')

    class Meta:
        db_table = 'precision_risk_predictions'
        verbose_name = '风险预测'
        verbose_name_plural = '风险预测'
        ordering = ['-predicted_at']

    def __str__(self):
        return f"{self.testcase.title}: {self.risk_score:.2f} ({self.risk_level})"


class PrecisionRunRecord(models.Model):
    """精准回归执行记录"""
    STATUS_CHOICES = [
        ('pending', '排队中'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]

    impact_analysis = models.ForeignKey(
        ImpactAnalysis, on_delete=models.CASCADE, related_name='precision_runs',
        verbose_name='关联影响分析'
    )
    selected_testcases = models.JSONField(default=list, verbose_name='选中用例ID列表')
    total_testcases = models.IntegerField(default=0, verbose_name='项目总用例数')
    reduction_rate = models.FloatField(default=0.0, verbose_name='缩减率')
    run_plan = models.ForeignKey(
        TestPlan, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='precision_runs', verbose_name='关联测试计划'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending',
        verbose_name='状态'
    )
    task_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='异步任务ID')
    progress = models.IntegerField(default=0, verbose_name='进度(%)')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'precision_run_records'
        verbose_name = '精准回归执行'
        verbose_name_plural = '精准回归执行'
        ordering = ['-created_at']

    def __str__(self):
        return f"Run {self.id}: {self.reduction_rate:.1%} reduction"
