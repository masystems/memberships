# Generated by Django 3.1.2 on 2021-02-15 10:02

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0092_membershippackage_payment_reminder_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershipsubscription',
            name='membership_start',
            field=models.DateField(blank=True, default=datetime.datetime.now, null=True),
        ),
    ]
