# Generated for adding report_status to TestExecution

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0010_add_suite_case_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='testexecution',
            name='report_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PENDING', '待生成'),
                    ('GENERATING', '生成中'),
                    ('SUCCESS', '成功'),
                    ('FAILED', '失败'),
                    ('SKIPPED', '跳过'),
                ],
                default='PENDING',
                verbose_name='报告生成状态'
            ),
        ),
    ]
