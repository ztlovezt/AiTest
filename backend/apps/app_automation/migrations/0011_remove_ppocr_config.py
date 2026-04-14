# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_automation', '0010_apptestconfig_ocr_engine_apptestconfig_ocr_language_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apptestconfig',
            name='ocr_use_gpu',
        ),
        migrations.AlterField(
            model_name='apptestconfig',
            name='ocr_engine',
            field=models.CharField(choices=[('tesseract', 'Tesseract OCR')], default='tesseract', help_text='APP自动化测试使用的 OCR 引擎', max_length=20, verbose_name='OCR 引擎'),
        ),
    ]
