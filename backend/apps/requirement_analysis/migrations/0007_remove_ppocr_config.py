# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0006_requirementdocument_extraction_warning'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='aimodelconfig',
            name='ocr_use_gpu',
        ),
        migrations.AlterField(
            model_name='aimodelconfig',
            name='ocr_provider',
            field=models.CharField(blank=True, choices=[('tesseract', 'Tesseract OCR'), ('openai', 'OpenAI GPT-4V'), ('zhipu', '智谱 GLM-4V'), ('baidu', '百度 AI OCR'), ('tencent', '腾讯 OCR'), ('aliyun', '阿里云 OCR'), ('custom', '自定义 OCR')], max_length=20, null=True, verbose_name='OCR 服务提供商'),
        ),
    ]
