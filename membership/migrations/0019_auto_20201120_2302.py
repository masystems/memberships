# Generated by Django 3.1.2 on 2020-11-20 23:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0018_membershippackage_stripe_acct_owner_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='email',
            field=models.EmailField(max_length=255, unique=True),
        ),
    ]
