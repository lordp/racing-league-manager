# Generated by Django 2.2 on 2019-04-28 07:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0049_auto_20190405_1707'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='slug',
            field=models.SlugField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
