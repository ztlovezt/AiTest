# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0005_add_ocr_config_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='requirementdocument',
            name='extraction_warning',
            field=models.TextField(blank=True, default='', verbose_name='提取警告信息'),
        ),
        migrations.AddField(
            model_name='requirementdocument',
            name='extraction_error',
            field=models.TextField(blank=True, default='', verbose_name='提取错误信息'),
        ),
    ]
