"""精准测试模块 DRF 序列化器"""
from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import serializers
from .models import (
    RepoBinding,
    CodeChangeAnalysis,
    TestCaseCodeMapping,
    ImpactAnalysis,
    RiskPredictionRecord,
    PrecisionRunRecord,
)


class RepoBindingSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    last_analyzed_at = serializers.SerializerMethodField()
    # Frontend-facing aliases
    local_path = serializers.CharField(source='repo_path', required=False, allow_blank=True)
    branch = serializers.CharField(source='default_branch', required=False, allow_blank=True)

    class Meta:
        model = RepoBinding
        fields = [
            'id', 'project', 'project_name', 'name', 'repo_url', 'repo_path',
            'local_path', 'branch', 'default_branch', 'last_analyzed_at',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True},
            'repo_url': {'required': False, 'allow_blank': True},
            'repo_path': {'required': False, 'allow_blank': True},
            'default_branch': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs: dict) -> dict:
        if self.instance is None and 'project' not in attrs:
            raise serializers.ValidationError(
                {'project': 'This field is required.'}
            )
        return attrs

    def get_last_analyzed_at(self, obj: RepoBinding) -> str | None:
        annotated_value = getattr(obj, 'last_analyzed_at', None)
        if annotated_value:
            return annotated_value.isoformat()

        latest_analysis = obj.analyses.order_by('-completed_at', '-created_at').first()
        if not latest_analysis:
            return None

        last_analyzed_at = latest_analysis.completed_at or latest_analysis.created_at
        return last_analyzed_at.isoformat() if last_analyzed_at else None


class CodeChangeAnalysisSerializer(serializers.ModelSerializer):
    """变更分析序列化器 — 前端兼容字段。

    扩展字段(供前端 ChangeAnalyses.vue 详情页直接消费):
        - commit_hash : head_commit 的别名
        - branch      : repo_binding.default_branch 别名
        - commit_time : 头部 commit 的提交时间(ISO),通过 GitDiffAnalyzer 实时查询
        - commit_message : 头部 commit 的提交说明,通过 GitDiffAnalyzer 实时查询
        - changed_files_count : 变更文件数
        - changed_functions_count : 变更函数数
        - changed_files : 在原始 JSON 基础上注入:
            * added       (新增行数 = len(added_lines))
            * removed     (删除行数 = len(removed_lines))
            * functions   (按 path 分组后的 changed_functions 列表)
    """
    project_name = serializers.CharField(source='repo_binding.project.name', read_only=True)
    branch = serializers.CharField(source='repo_binding.default_branch', read_only=True)
    commit_hash = serializers.CharField(source='head_commit', read_only=True)
    commit_time = serializers.SerializerMethodField()
    commit_message = serializers.SerializerMethodField()
    changed_files = serializers.SerializerMethodField()
    changed_files_count = serializers.SerializerMethodField()
    changed_functions_count = serializers.SerializerMethodField()

    class Meta:
        model = CodeChangeAnalysis
        fields = [
            'id', 'repo_binding', 'project_name', 'branch',
            'base_commit', 'head_commit', 'commit_hash',
            'commit_time', 'commit_message',
            'changed_files', 'changed_functions',
            'changed_files_count', 'changed_functions_count',
            'status', 'progress',
            'error_message', 'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = [
            'changed_files', 'changed_functions', 'status', 'progress',
            'error_message', 'started_at', 'completed_at', 'created_at',
        ]

    # ------------------------------------------------------------------
    # 计算字段实现
    # ------------------------------------------------------------------
    def get_changed_files_count(self, obj: CodeChangeAnalysis) -> int:
        return len(obj.changed_files or [])

    def get_changed_functions_count(self, obj: CodeChangeAnalysis) -> int:
        return len(obj.changed_functions or [])

    def get_changed_files(self, obj: CodeChangeAnalysis) -> list[dict]:
        """注入每个文件的 added/removed/functions 字段,供前端表格直接消费。"""
        files = obj.changed_files or []
        functions = obj.changed_functions or []
        # 按文件路径分组函数
        funcs_by_path: dict[str, list[dict]] = {}
        for func in functions:
            if not isinstance(func, dict):
                continue
            path = func.get('file') or func.get('file_path') or ''
            if not path:
                continue
            funcs_by_path.setdefault(path, []).append(func)

        enriched: list[dict] = []
        for f in files:
            if not isinstance(f, dict):
                continue
            path = f.get('path', '')
            file_funcs = funcs_by_path.get(path, [])
            file_change_type = f.get('change_type', 'modified')
            normalized_funcs = [
                {
                    'name': fn.get('name') or fn.get('qualified_name', ''),
                    'qualified_name': fn.get('qualified_name', ''),
                    'signature': fn.get('signature', ''),
                    'class_name': fn.get('class_name', ''),
                    'start_line': fn.get('start_line'),
                    'end_line': fn.get('end_line'),
                    'change_type': fn.get('change_type', file_change_type),
                    'is_async': fn.get('is_async', False),
                }
                for fn in file_funcs
            ]
            enriched.append({
                **f,
                'added': len(f.get('added_lines') or []),
                'removed': len(f.get('removed_lines') or []),
                'functions': normalized_funcs,
            })
        return enriched

    def get_commit_time(self, obj: CodeChangeAnalysis) -> str | None:
        info = self._get_head_commit_info(obj)
        if info:
            return info.get('committed_datetime')
        # 回退:使用记录的完成时间
        if obj.completed_at:
            return obj.completed_at.isoformat()
        return None

    def get_commit_message(self, obj: CodeChangeAnalysis) -> str:
        info = self._get_head_commit_info(obj)
        if info:
            return info.get('message', '')
        return ''

    def _get_head_commit_info(self, obj: CodeChangeAnalysis) -> dict | None:
        """惰性查询 head commit 元数据。

        仅在 retrieve 调用上下文执行 git 操作,避免 list 接口性能开销。
        查询结果在单次序列化生命周期内缓存,避免重复 git 调用。
        """
        # 列表接口跳过昂贵的 git 查询
        view = self.context.get('view')
        if view is not None and getattr(view, 'action', None) == 'list':
            return None

        cache_key = f'_commit_info_{obj.pk}'
        if cache_key in self.context:
            return self.context[cache_key]

        result: dict | None = None
        try:
            repo_binding = obj.repo_binding
            repo_path = getattr(repo_binding, 'repo_path', None)
            if not repo_path or not obj.head_commit:
                self.context[cache_key] = None
                return None
            from .git_analyzer import GitDiffAnalyzer
            analyzer = GitDiffAnalyzer(repo_path=repo_path)
            result = analyzer.get_commit_info(obj.head_commit)
        except Exception as exc:  # noqa: BLE001 — 容错降级,不应阻断详情接口
            import logging
            logging.getLogger(__name__).warning(
                'CodeChangeAnalysis %s 获取 commit 元数据失败: %s', obj.pk, exc
            )
            result = None
        self.context[cache_key] = result
        return result


class TestCaseCodeMappingSerializer(serializers.ModelSerializer):
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    confidence = serializers.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )

    class Meta:
        model = TestCaseCodeMapping
        fields = [
            'id', 'testcase', 'testcase_title', 'function_signature',
            'file_path', 'mapping_type', 'confidence',
            'created_by', 'created_by_username', 'created_at',
        ]
        read_only_fields = ['created_at']


class ImpactAnalysisSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(
        source='change_analysis.repo_binding.project.name', read_only=True
    )
    commit_range = serializers.SerializerMethodField()

    class Meta:
        model = ImpactAnalysis
        fields = [
            'id', 'change_analysis', 'project_name', 'commit_range',
            'impacted_functions', 'impacted_testcases',
            'min_regression_set', 'regression_time_estimate',
            'status', 'created_at',
        ]
        read_only_fields = ['status', 'created_at']

    def get_commit_range(self, obj: ImpactAnalysis) -> str:
        return (
            f"{obj.change_analysis.base_commit[:7]}.."
            f"{obj.change_analysis.head_commit[:7]}"
        )


class RiskPredictionRecordSerializer(serializers.ModelSerializer):
    testcase_title = serializers.CharField(source='testcase.title', read_only=True)

    class Meta:
        model = RiskPredictionRecord
        fields = [
            'id', 'testcase', 'testcase_title', 'impact_analysis',
            'risk_score', 'risk_level', 'features', 'model_version', 'predicted_at',
        ]
        read_only_fields = ['predicted_at']


class PrecisionRunRecordSerializer(serializers.ModelSerializer):
    impact_commit_range = serializers.SerializerMethodField()
    repo_name = serializers.SerializerMethodField()
    branch = serializers.SerializerMethodField()
    commit_hash = serializers.SerializerMethodField()
    triggered_at = serializers.SerializerMethodField()
    duration_seconds = serializers.SerializerMethodField()
    error_message = serializers.CharField(read_only=True)
    selected_case_count = serializers.SerializerMethodField()
    total_case_count = serializers.SerializerMethodField()
    selected_cases = serializers.SerializerMethodField()

    class Meta:
        model = PrecisionRunRecord
        fields = [
            'id', 'impact_analysis', 'impact_commit_range',
            'repo_name', 'branch', 'commit_hash',
            'selected_testcases', 'selected_cases', 'selected_case_count',
            'total_testcases', 'total_case_count', 'reduction_rate',
            'run_plan', 'status', 'progress', 'task_id',
            'started_at', 'triggered_at', 'completed_at', 'duration_seconds',
            'error_message', 'created_at',
        ]
        read_only_fields = [
            'status', 'progress', 'started_at', 'completed_at', 'created_at', 'task_id',
        ]

    def get_impact_commit_range(self, obj: PrecisionRunRecord) -> str:
        ca = obj.impact_analysis.change_analysis
        return f"{ca.base_commit[:7]}..{ca.head_commit[:7]}"

    def get_repo_name(self, obj: PrecisionRunRecord) -> str | None:
        try:
            return obj.impact_analysis.change_analysis.repo_binding.project.name
        except AttributeError:
            return None

    def get_branch(self, obj: PrecisionRunRecord) -> str | None:
        try:
            return obj.impact_analysis.change_analysis.repo_binding.default_branch
        except AttributeError:
            return None

    def get_commit_hash(self, obj: PrecisionRunRecord) -> str | None:
        try:
            return obj.impact_analysis.change_analysis.head_commit
        except AttributeError:
            return None

    def get_triggered_at(self, obj: PrecisionRunRecord) -> str | None:
        if obj.started_at:
            return obj.started_at.isoformat()
        return None

    def get_duration_seconds(self, obj: PrecisionRunRecord) -> float | None:
        if obj.completed_at and obj.started_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None

    def get_selected_case_count(self, obj: PrecisionRunRecord) -> int:
        return len(obj.selected_testcases or [])

    def get_total_case_count(self, obj: PrecisionRunRecord) -> int:
        return obj.total_testcases

    def get_selected_cases(self, obj: PrecisionRunRecord) -> list[dict]:
        ids = obj.selected_testcases or []
        if not ids:
            return []
        from apps.testcases.models import TestCase
        cases = TestCase.objects.filter(id__in=ids).values('id', 'title')
        return [
            {
                'id': c['id'],
                'name': c['title'],
                'risk_score': None,  # MVP: 前端显示时暂无风险分，可后续关联 RiskPredictionRecord
            }
            for c in cases
        ]


class TestCaseCodeMappingBulkSerializer(serializers.Serializer):
    """Phase 1 手工标注批量导入。

    校验:
        - mappings 列表非空
        - 每条记录通过单条 Serializer 校验
        - 同一 (testcase, function_signature) 自动 update_or_create
    """

    mappings = TestCaseCodeMappingSerializer(many=True)

    def create(self, validated_data: dict) -> dict:
        items = validated_data["mappings"]
        if not items:
            raise serializers.ValidationError({"mappings": "至少包含一条标注"})
        created_count = 0
        updated_count = 0
        for item in items:
            testcase = item.pop("testcase")
            function_signature = item.pop("function_signature")
            _, created = TestCaseCodeMapping.objects.update_or_create(
                testcase=testcase,
                function_signature=function_signature,
                defaults=item,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        return {"created": created_count, "updated": updated_count, "total": len(items)}


CSV_REQUIRED_HEADERS = (
    "testcase_id",
    "function_signature",
    "file_path",
    "mapping_type",
    "confidence",
)


class TestCaseCodeMappingCsvImportSerializer(serializers.Serializer):
    """CSV 导入序列化器。

    输入:
        - file: 上传的 CSV 文件(multipart/form-data)
        - or rows: 已解析的字典列表(单测友好)

    Schema 5 列: testcase_id, function_signature, file_path, mapping_type, confidence
    """

    file = serializers.FileField(required=False)
    rows = serializers.ListField(child=serializers.DictField(), required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("file") and not attrs.get("rows"):
            raise serializers.ValidationError("必须上传 file 或提供 rows")
        return attrs

    def create(self, validated_data: dict) -> dict:
        rows = validated_data.get("rows") or self._parse_csv(validated_data["file"])
        return self._persist(rows)

    @staticmethod
    def _parse_csv(file_obj) -> list[dict]:
        import csv
        import io

        raw = file_obj.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(raw))
        if not reader.fieldnames:
            raise serializers.ValidationError("CSV 文件为空或缺少表头")
        missing = [h for h in CSV_REQUIRED_HEADERS if h not in reader.fieldnames]
        if missing:
            raise serializers.ValidationError(f"缺少表头列: {missing}")
        return [row for row in reader]

    @staticmethod
    def _persist(rows: list[dict]) -> dict:
        from django.db import transaction
        from apps.testcases.models import TestCase

        errors: list[dict] = []
        created = 0
        updated = 0
        with transaction.atomic():
            for line_no, row in enumerate(rows, start=2):  # 表头算第 1 行
                try:
                    testcase_id = int(row["testcase_id"])
                    function_signature = (row.get("function_signature") or "").strip()
                    file_path = (row.get("file_path") or "").strip()
                    mapping_type = (row.get("mapping_type") or "manual").strip()
                    confidence = float(row.get("confidence") or 1.0)

                    if not function_signature:
                        raise ValueError("function_signature 为空")
                    if mapping_type not in ("manual", "auto_static", "auto_dynamic"):
                        raise ValueError(f"非法 mapping_type: {mapping_type}")
                    if not 0.0 <= confidence <= 1.0:
                        raise ValueError(f"confidence 越界: {confidence}")

                    if not TestCase.objects.filter(id=testcase_id).exists():
                        raise ValueError(f"testcase_id={testcase_id} 不存在")

                    _, was_created = TestCaseCodeMapping.objects.update_or_create(
                        testcase_id=testcase_id,
                        function_signature=function_signature,
                        defaults={
                            "file_path": file_path,
                            "mapping_type": mapping_type,
                            "confidence": confidence,
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except (KeyError, ValueError, TypeError) as exc:
                    errors.append({"line": line_no, "row": row, "error": str(exc)})

        return {
            "created": created,
            "updated": updated,
            "total": len(rows),
            "errors": errors,
        }
