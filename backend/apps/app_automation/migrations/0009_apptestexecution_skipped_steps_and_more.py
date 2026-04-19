# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_automation', '0008_alter_apptestexecution_report_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='apptestexecution',
            name='skipped_steps',
            field=models.IntegerField(default=0, verbose_name='跳过步骤数'),
        ),
        migrations.AddField(
            model_name='apptestexecution',
            name='result_data',
            field=models.JSONField(blank=True, null=True, verbose_name='执行结果数据'),
        ),
    ]
