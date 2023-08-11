# Generated by Django 4.0.5 on 2023-08-11 03:41

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_loginlog_collectorsynclog'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='collector',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='collector', to=settings.AUTH_USER_MODEL, verbose_name='Collector'),
        ),
    ]