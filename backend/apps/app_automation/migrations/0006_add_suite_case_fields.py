# Generated migration for adding suite-level fields to AppTestSuiteCase

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_automation', '0005_appproject_unified_meta_project'),
    ]

    operations = [
        migrations.AddField(
            model_name='apptestsuitecase',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='是否启用'),
        ),
        migrations.AddField(
            model_name='apptestsuitecase',
            name='extract_variables',
            field=models.JSONField(blank=True, default=list, verbose_name='变量提取规则'),
        ),
        migrations.AddField(
            model_name='apptestsuitecase',
            name='skip_condition',
            field=models.TextField(blank=True, default='', verbose_name='跳过条件'),
        ),
    ]
