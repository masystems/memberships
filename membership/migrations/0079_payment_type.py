# Generated by Django 3.1.2 on 2021-01-15 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0078_merge_20210114_1532'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='type',
            field=models.CharField(choices=[('subscription', 'Subscription'), ('donation', 'Donation '), ('merchandise', 'Merchandise '), ('fees', 'Fees '), ('adverts', 'Adverts ')], default='subscription', max_length=25, null=True, verbose_name='Payment Type'),
        ),
    ]
