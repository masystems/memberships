# Generated by Django 3.1.2 on 2021-01-13 08:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0072_auto_20210113_0743'),
    ]

    operations = [
        migrations.AddField(
            model_name='equine',
            name='actual_renewal',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='equine',
            name='bank_account_number',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='bank_address',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='bank_sort_code',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='so_amount',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='so_started',
            field=models.DateField(blank=True, null=True),
        ),
    ]
