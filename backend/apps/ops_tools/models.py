from django.conf import settings
from django.db import models


class OpsEnvironmentCategory(models.Model):
    """运维环境分类。"""

    name = models.CharField(max_length=100, verbose_name="分类名称")
    code = models.CharField(max_length=50, unique=True, verbose_name="分类编码")
    description = models.TextField(blank=True, default="", verbose_name="分类说明")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ops_environment_category"
        verbose_name = "运维环境分类"
        verbose_name_plural = "运维环境分类"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name}({self.code})"


class OpsEnvironmentCategoryDirectory(models.Model):
    """分类下可访问的日志目录。"""

    category = models.ForeignKey(
        OpsEnvironmentCategory,
        on_delete=models.CASCADE,
        related_name="directories",
        verbose_name="所属分类",
    )
    name = models.CharField(max_length=100, verbose_name="目录名称")
    path = models.CharField(max_length=500, verbose_name="目录路径")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ops_environment_category_directory"
        verbose_name = "分类目录"
        verbose_name_plural = "分类目录"
        ordering = ["sort_order", "id"]
        unique_together = [("category", "path")]

    def __str__(self):
        return f"{self.category.name}-{self.name}"


class OpsEnvironment(models.Model):
    """运维环境配置。"""

    TYPE_DEV = "dev"
    TYPE_TEST = "test"
    TYPE_STAGING = "staging"
    TYPE_PROD = "prod"
    TYPE_OTHER = "other"

    ACCESS_LOCAL = "local"
    ACCESS_SSH = "ssh"

    ENVIRONMENT_TYPE_CHOICES = [
        (TYPE_DEV, "开发"),
        (TYPE_TEST, "测试"),
        (TYPE_STAGING, "预发布"),
        (TYPE_PROD, "生产"),
        (TYPE_OTHER, "其他"),
    ]

    ACCESS_MODE_CHOICES = [
        (ACCESS_LOCAL, "本机"),
        (ACCESS_SSH, "SSH"),
    ]

    category = models.ForeignKey(
        OpsEnvironmentCategory,
        on_delete=models.PROTECT,
        related_name="environments",
        null=True,
        blank=True,
        verbose_name="环境分类",
    )
    name = models.CharField(max_length=100, verbose_name="环境名称")
    env_code = models.CharField(max_length=50, unique=True, verbose_name="环境编码")
    environment_type = models.CharField(
        max_length=20,
        choices=ENVIRONMENT_TYPE_CHOICES,
        default=TYPE_TEST,
        verbose_name="环境类型",
    )
    access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_MODE_CHOICES,
        default=ACCESS_SSH,
        verbose_name="接入方式",
    )
    description = models.TextField(blank=True, default="", verbose_name="环境说明")
    # 保留旧字段，兼容已有数据。新日志查询优先读取分类目录配置。
    log_root = models.CharField(max_length=500, blank=True, default="", verbose_name="日志根目录")

    ssh_host = models.CharField(max_length=255, blank=True, default="", verbose_name="SSH 主机")
    ssh_port = models.PositiveIntegerField(default=22, verbose_name="SSH 端口")
    ssh_username = models.CharField(max_length=255, blank=True, default="", verbose_name="SSH 用户名")
    ssh_password = models.CharField(max_length=255, blank=True, default="", verbose_name="SSH 密码")

    client_url = models.CharField(max_length=500, blank=True, default="", verbose_name="客户端地址")
    admin_url = models.CharField(max_length=500, blank=True, default="", verbose_name="管理端地址")
    official_url = models.CharField(max_length=500, blank=True, default="", verbose_name="官网地址")
    image_host = models.CharField(max_length=500, blank=True, default="", verbose_name="图片主机")

    mysql_config = models.JSONField(default=dict, blank=True, verbose_name="MySQL 配置")
    redis_config = models.JSONField(default=dict, blank=True, verbose_name="Redis 配置")
    mongo_config = models.JSONField(default=dict, blank=True, verbose_name="MongoDB 配置")
    extra_config = models.JSONField(default=dict, blank=True, verbose_name="扩展配置")

    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_ops_environments",
        verbose_name="创建人",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_ops_environments",
        verbose_name="更新人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "ops_environment"
        verbose_name = "运维环境"
        verbose_name_plural = "运维环境"
        ordering = ["-updated_at", "-id"]

    def __str__(self):
        return f"{self.name}({self.env_code})"
