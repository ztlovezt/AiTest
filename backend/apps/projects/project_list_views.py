from django.db import models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.unified_projects.models import MetaProject
from apps.unified_projects.services import ensure_ai_project_for_meta_project

from .models import Project


import logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_projects_list(request):
    """获取用户有权限访问的项目列表，用于下拉选择。"""
    user = request.user
    logger.info(f"[user_projects_list] user={user}, is_superuser={user.is_superuser}, is_authenticated={user.is_authenticated}")
    accessible_meta_projects = MetaProject.objects.filter(
        models.Q(owner=user) | models.Q(members__user=user)
    ).select_related('owner').distinct()

    for meta_project in accessible_meta_projects:
        ensure_ai_project_for_meta_project(meta_project)

    # superuser 查看所有项目；普通用户按归属/member/统一项目过滤
    if user.is_superuser:
        projects = Project.objects.all().values('id', 'name', 'status').order_by('name')
        logger.info(f"[user_projects_list] superuser path: {list(projects)}")
    else:
        projects = Project.objects.filter(
            models.Q(owner=user)
            | models.Q(members=user)
            | models.Q(unified_meta_project__in=accessible_meta_projects)
        ).distinct().values('id', 'name', 'status').order_by('name')
        logger.info(f"[user_projects_list] normal path: {list(projects)}")

    return Response({
        'results': list(projects)
    })