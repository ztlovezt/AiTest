from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OpsEnvironmentCategoryViewSet,
    OpsEnvironmentViewSet,
    OpsLogViewSet,
)

router = DefaultRouter()
router.register(r"categories", OpsEnvironmentCategoryViewSet, basename="ops-category")
router.register(r"environments", OpsEnvironmentViewSet, basename="ops-environment")
router.register(r"logs", OpsLogViewSet, basename="ops-log")

urlpatterns = [
    path("", include(router.urls)),
]
