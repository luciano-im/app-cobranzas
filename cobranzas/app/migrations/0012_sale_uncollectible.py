# Generated by Django 4.0.5 on 2023-09-18 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0011_delete_collectorsynclog'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='uncollectible',
            field=models.BooleanField(default=False, verbose_name='Is uncollectible?'),
        ),
    ]
