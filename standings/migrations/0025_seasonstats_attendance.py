# Generated by Django 2.0.4 on 2018-06-07 03:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0024_trackrecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='seasonstats',
            name='attendance',
            field=models.IntegerField(default=0),
        ),
    ]
