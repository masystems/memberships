# Generated by Django 3.1.2 on 2021-03-17 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0098_auto_20210316_1419'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='address_line_1',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='postcode',
            field=models.CharField(max_length=255),
        ),
    ]
