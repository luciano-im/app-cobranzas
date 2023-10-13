# Generated by Django 4.0.5 on 2023-10-13 03:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collection', '0004_collectiondelivery'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectiondelivery',
            name='collector',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Collector'),
            preserve_default=False,
        ),
    ]
