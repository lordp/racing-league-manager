# Generated by Django 2.0.7 on 2018-08-23 02:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0038_auto_20180822_1044'),
    ]

    operations = [
        migrations.AlterField(
            model_name='season',
            name='classification_type',
            field=models.CharField(blank=True, choices=[('', 'No classification'), ('percent', 'Percentage'), ('laps', 'Laps')], max_length=10),
        ),
    ]
