# Generated by Django 3.1.2 on 2021-03-23 10:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0101_payment_stripe_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipsubscription',
            name='remaining_amount',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
