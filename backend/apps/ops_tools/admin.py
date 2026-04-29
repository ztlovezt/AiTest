from django.contrib import admin

from .models import (
    OpsEnvironment,
    OpsEnvironmentCategory,
    OpsEnvironmentCategoryDirectory,
)


class OpsEnvironmentCategoryDirectoryInline(admin.TabularInline):
    model = OpsEnvironmentCategoryDirectory
    extra = 0


@admin.register(OpsEnvironmentCategory)
class OpsEnvironmentCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "sort_order", "is_active", "updated_at")
    search_fields = ("name", "code", "description")
    list_filter = ("is_active",)
    inlines = [OpsEnvironmentCategoryDirectoryInline]


@admin.register(OpsEnvironment)
class OpsEnvironmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "env_code",
        "category",
        "environment_type",
        "access_mode",
        "is_active",
        "updated_at",
    )
    list_filter = ("category", "environment_type", "access_mode", "is_active")
    search_fields = ("name", "env_code", "ssh_host", "category__name")
