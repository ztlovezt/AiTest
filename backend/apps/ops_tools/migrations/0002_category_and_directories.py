from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("ops_tools", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OpsEnvironmentCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="分类名称")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="分类编码")),
                ("description", models.TextField(blank=True, default="", verbose_name="分类说明")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "运维环境分类",
                "verbose_name_plural": "运维环境分类",
                "db_table": "ops_environment_category",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="OpsEnvironmentCategoryDirectory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="目录名称")),
                ("path", models.CharField(max_length=500, verbose_name="目录路径")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="directories",
                        to="ops_tools.opsenvironmentcategory",
                        verbose_name="所属分类",
                    ),
                ),
            ],
            options={
                "verbose_name": "分类目录",
                "verbose_name_plural": "分类目录",
                "db_table": "ops_environment_category_directory",
                "ordering": ["sort_order", "id"],
                "unique_together": {("category", "path")},
            },
        ),
        migrations.AddField(
            model_name="opsenvironment",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="environments",
                to="ops_tools.opsenvironmentcategory",
                verbose_name="环境分类",
            ),
        ),
        migrations.AlterField(
            model_name="opsenvironment",
            name="access_mode",
            field=models.CharField(
                choices=[("local", "本机"), ("ssh", "SSH")],
                default="ssh",
                max_length=20,
                verbose_name="接入方式",
            ),
        ),
    ]
