# Generated by Django 3.1.2 on 2021-01-04 22:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0050_auto_20210104_0009'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='membershipsubscription',
            name='created',
        ),
        migrations.AddField(
            model_name='membershipsubscription',
            name='membership_start',
            field=models.DateTimeField(auto_now=True),
        ),
    ]