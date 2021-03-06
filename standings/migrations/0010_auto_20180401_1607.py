# Generated by Django 2.0.1 on 2018-04-01 04:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0009_auto_20180331_2004'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='result',
            options={'ordering': ['position']},
        ),
        migrations.AddField(
            model_name='result',
            name='fastest_lap_value',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='result',
            name='gap',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='result',
            name='lap_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='result',
            name='points',
            field=models.IntegerField(default=0),
        ),
    ]
