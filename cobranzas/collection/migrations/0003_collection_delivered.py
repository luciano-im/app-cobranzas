# Generated by Django 4.0.5 on 2023-10-10 04:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collection', '0002_collectorsynclog'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='delivered',
            field=models.BooleanField(default=False, verbose_name='Cobranza Rendida'),
        ),
    ]
