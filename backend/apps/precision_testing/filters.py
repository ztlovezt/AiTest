"""精准测试模块 DRF FilterSet 定义"""
from django_filters import rest_framework as filters
from .models import PrecisionRunRecord


class PrecisionRunRecordFilter(filters.FilterSet):
    """精准回归执行记录过滤器。

    支持查询参数:
        - ``status``: 精确匹配状态 (pending/running/completed/failed)
        - ``start_date``: ``started_at >= start_date`` (YYYY-MM-DD)
        - ``end_date``: ``started_at <= end_date`` (YYYY-MM-DD)
    """

    start_date = filters.DateFilter(field_name='started_at', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='started_at', lookup_expr='lte')

    class Meta:
        model = PrecisionRunRecord
        fields = ['status']
