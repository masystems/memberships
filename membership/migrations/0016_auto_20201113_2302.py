# Generated by Django 3.1.2 on 2020-11-13 23:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0015_auto_20201111_2312'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershippackage',
            name='organisation_name',
            field=models.CharField(max_length=50),
        ),
    ]
