from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OpsEnvironment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="环境名称")),
                ("env_code", models.CharField(max_length=50, unique=True, verbose_name="环境编码")),
                ("environment_type", models.CharField(choices=[("dev", "开发"), ("test", "测试"), ("staging", "预发布"), ("prod", "生产"), ("other", "其他")], default="test", max_length=20, verbose_name="环境类型")),
                ("access_mode", models.CharField(choices=[("local", "本机"), ("ssh", "SSH")], default="local", max_length=20, verbose_name="接入方式")),
                ("description", models.TextField(blank=True, default="", verbose_name="环境说明")),
                ("log_root", models.CharField(blank=True, default="", max_length=500, verbose_name="日志根目录")),
                ("ssh_host", models.CharField(blank=True, default="", max_length=255, verbose_name="SSH 主机")),
                ("ssh_port", models.PositiveIntegerField(default=22, verbose_name="SSH 端口")),
                ("ssh_username", models.CharField(blank=True, default="", max_length=255, verbose_name="SSH 用户名")),
                ("ssh_password", models.CharField(blank=True, default="", max_length=255, verbose_name="SSH 密码")),
                ("client_url", models.CharField(blank=True, default="", max_length=500, verbose_name="客户端地址")),
                ("admin_url", models.CharField(blank=True, default="", max_length=500, verbose_name="管理端地址")),
                ("official_url", models.CharField(blank=True, default="", max_length=500, verbose_name="官网地址")),
                ("image_host", models.CharField(blank=True, default="", max_length=500, verbose_name="镜像地址")),
                ("mysql_config", models.JSONField(blank=True, default=dict, verbose_name="MySQL 配置")),
                ("redis_config", models.JSONField(blank=True, default=dict, verbose_name="Redis 配置")),
                ("mongo_config", models.JSONField(blank=True, default=dict, verbose_name="Mongo 配置")),
                ("extra_config", models.JSONField(blank=True, default=dict, verbose_name="扩展配置")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_ops_environments", to=settings.AUTH_USER_MODEL, verbose_name="创建人")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_ops_environments", to=settings.AUTH_USER_MODEL, verbose_name="更新人")),
            ],
            options={
                "verbose_name": "运维环境",
                "verbose_name_plural": "运维环境",
                "db_table": "ops_environment",
                "ordering": ["-updated_at", "-id"],
            },
        ),
    ]

