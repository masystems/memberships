# Generated by Django 3.1.2 on 2021-01-10 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0061_auto_20210110_2015'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equine',
            name='animal_owner',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='equine',
            name='badge',
            field=models.BooleanField(default=False),
        ),
    ]
