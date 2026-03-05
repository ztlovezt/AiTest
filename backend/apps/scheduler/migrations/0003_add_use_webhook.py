# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0002_update_schedule_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconfig',
            name='use_webhook',
            field=models.BooleanField(default=False, verbose_name='使用Webhook通知'),
        ),
    ]
