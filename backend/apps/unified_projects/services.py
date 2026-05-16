from django.db import transaction

from apps.projects.models import Project

from .models import MetaProject, MetaProjectMember, ProjectModule


@transaction.atomic
def ensure_ai_project_for_meta_project(meta_project: MetaProject) -> Project:
    """确保元项目具备 AI 模块与对应的 ``projects.Project`` 记录。"""
    MetaProjectMember.objects.get_or_create(
        meta_project=meta_project,
        user=meta_project.owner,
        defaults={'role': 'owner'},
    )
    ProjectModule.objects.get_or_create(
        meta_project=meta_project,
        module_type='AI',
        defaults={'config': {}},
    )

    project = Project.objects.filter(unified_meta_project=meta_project).first()
    if project:
        updated_fields = []
        if project.name != meta_project.name:
            project.name = meta_project.name
            updated_fields.append('name')
        if project.description != meta_project.description:
            project.description = meta_project.description
            updated_fields.append('description')
        if project.status != meta_project.status:
            project.status = meta_project.status
            updated_fields.append('status')
        if project.owner_id != meta_project.owner_id:
            project.owner = meta_project.owner
            updated_fields.append('owner')
        if project.unified_meta_project_id != meta_project.id:
            project.unified_meta_project = meta_project
            updated_fields.append('unified_meta_project')
        if updated_fields:
            project.save(update_fields=updated_fields)
        return project

    return Project.objects.create(
        name=meta_project.name,
        description=meta_project.description,
        status=meta_project.status,
        owner=meta_project.owner,
        unified_meta_project=meta_project,
    )
