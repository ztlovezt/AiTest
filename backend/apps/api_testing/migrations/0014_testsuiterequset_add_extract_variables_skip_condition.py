from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api_testing', '0013_apirequest_extract_variables'),
    ]

    operations = [
        migrations.AddField(
            model_name='testsuiterequest',
            name='extract_variables',
            field=models.JSONField(default=list, blank=True, verbose_name='变量提取规则'),
        ),
        migrations.AddField(
            model_name='testsuiterequest',
            name='skip_condition',
            field=models.TextField(blank=True, default='', verbose_name='跳过条件'),
        ),
    ]
