# Generated migration for adding report_status to TestExecution

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_testing', '0008_add_parameterized_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='testexecution',
            name='report_status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('PENDING', '待生成'),
                    ('GENERATING', '生成中'),
                    ('SUCCESS', '生成成功'),
                    ('FAILED', '生成失败'),
                    ('SKIPPED', '未生成'),
                ],
                default='PENDING',
                max_length=20,
                verbose_name='报告状态',
            ),
        ),
    ]
