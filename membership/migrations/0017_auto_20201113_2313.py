# Generated by Django 3.1.2 on 2020-11-13 23:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0016_auto_20201113_2302'),
    ]

    operations = [
        migrations.RenameField(
            model_name='membershippackage',
            old_name='stripe_id',
            new_name='stripe_acct_id',
        ),
    ]
