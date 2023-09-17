# Generated by Django 4.0.5 on 2023-09-17 20:29

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collection', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='CollectorSyncLog',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('sync_datetime', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date')),
                        ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='User')),
                    ],
                    options={
                        'verbose_name': 'Collector Synchronization Log',
                    },
                ),
            ],
            # Table already exists. See app/migrations/0011_delete_collectorsynclog.py
            database_operations=[],
        ),
    ]
