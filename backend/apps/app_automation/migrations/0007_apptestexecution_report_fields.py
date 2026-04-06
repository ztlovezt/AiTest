# Generated for adding report_url and report_status to AppTestExecution

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_automation', '0006_add_suite_case_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='apptestexecution',
            name='report_url',
            field=models.CharField(
                max_length=500,
                blank=True,
                default='',
                verbose_name='Allure报告URL'
            ),
        ),
        migrations.AddField(
            model_name='apptestexecution',
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
