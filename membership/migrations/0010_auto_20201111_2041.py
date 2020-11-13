# Generated by Django 3.1.2 on 2020-11-11 20:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0009_auto_20201111_2039'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='address_line_1',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='email',
            field=models.EmailField(max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='first_name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='member',
            name='last_name',
            field=models.CharField(max_length=255),
        ),
    ]
