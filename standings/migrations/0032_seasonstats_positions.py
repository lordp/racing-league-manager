# Generated by Django 2.0.4 on 2018-07-21 08:23

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0031_auto_20180720_1308'),
    ]

    operations = [
        migrations.AddField(
            model_name='seasonstats',
            name='positions',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
        ),
    ]