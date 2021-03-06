# Generated by Django 3.1.2 on 2021-01-03 14:33

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0044_donation_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='donation',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='donation',
            name='stripe_payment_id',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
