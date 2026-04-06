# Generated migration for adding suite-level fields to TestSuiteTestCase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0009_remove_aiexecutionrecord_ai_case_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='testsuitetestcase',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='是否启用'),
        ),
        migrations.AddField(
            model_name='testsuitetestcase',
            name='extract_variables',
            field=models.JSONField(blank=True, default=list, verbose_name='变量提取规则'),
        ),
        migrations.AddField(
            model_name='testsuitetestcase',
            name='skip_condition',
            field=models.TextField(blank=True, default='', verbose_name='跳过条件'),
        ),
    ]
