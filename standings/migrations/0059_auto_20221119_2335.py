# Generated by Django 2.2.28 on 2022-11-19 23:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('standings', '0058_auto_20221014_2116'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lap',
            name='compound',
            field=models.CharField(blank=True, max_length=50, verbose_name='Tyre Compound'),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c1',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c2',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c3',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c4',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c5',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c6',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='seasontyremap',
            name='c7',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]