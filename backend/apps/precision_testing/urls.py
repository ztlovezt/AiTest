"""精准测试模块 URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'repos', views.RepoBindingViewSet, basename='repo-binding')
router.register(r'analyses', views.CodeChangeAnalysisViewSet, basename='code-change-analysis')
router.register(r'mappings', views.TestCaseCodeMappingViewSet, basename='testcase-code-mapping')
router.register(r'impact', views.ImpactAnalysisViewSet, basename='impact-analysis')
router.register(r'predictions', views.RiskPredictionRecordViewSet, basename='risk-prediction')
router.register(r'runs', views.PrecisionRunRecordViewSet, basename='precision-run')

# 注意：自定义路由必须放在 include(router.urls) 之前，
# 否则 router 的 detail 模式（如 mappings/<pk>/）会截获 mappings/auto-build/ 这类路径
urlpatterns = [
    path('mappings/auto-build/', views.TestCaseCodeMappingViewSet.as_view({'post': 'auto_build'}), name='mapping-auto-build'),
    path('repos/<int:pk>/analyze/', views.RepoBindingViewSet.as_view({'post': 'analyze'}), name='repo-analyze'),
    path('analyses/<int:pk>/progress/', views.CodeChangeAnalysisViewSet.as_view({'get': 'progress'}), name='analysis-progress'),
    path('graph/', views.GraphDataView.as_view(), name='graph-data'),
    path('impact/query/', views.ImpactQueryView.as_view(), name='impact-query'),
    path('dashboard/', views.DashboardView.as_view(), name='precision-dashboard'),
    path('webhooks/git/', views.GitWebhookView.as_view(), name='git-webhook'),
    path('gate/', views.CoverageGateView.as_view(), name='coverage-gate'),
    path('', include(router.urls)),
]
