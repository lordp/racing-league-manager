# Generated by Django 2.0.1 on 2018-03-31 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0008_auto_20180331_1528'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pointsystem',
            name='qualifying_points',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
