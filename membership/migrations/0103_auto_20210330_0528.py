# Generated by Django 3.1.2 on 2021-03-30 05:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0102_membershipsubscription_remaining_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='company',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
