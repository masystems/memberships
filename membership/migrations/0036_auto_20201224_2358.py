# Generated by Django 3.1.2 on 2020-12-24 23:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0035_auto_20201224_1946'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='address_line_2',
            field=models.CharField(blank=True, default='', max_length=255),
            preserve_default=False,
        ),
    ]
