# Generated by Django 3.1.2 on 2020-12-29 23:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0037_auto_20201229_2154'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipsubscription',
            name='validated',
            field=models.BooleanField(default=False),
        ),
    ]