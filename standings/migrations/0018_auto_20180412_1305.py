# Generated by Django 2.0.1 on 2018-04-12 01:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0017_result_penalty_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointsystem',
            name='pole_position',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='pointsystem',
            name='fastest_lap',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='pointsystem',
            name='lead_lap',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='pointsystem',
            name='most_laps_lead',
            field=models.FloatField(default=0),
        ),
        migrations.AlterField(
            model_name='result',
            name='points',
            field=models.FloatField(default=0),
        ),
    ]
