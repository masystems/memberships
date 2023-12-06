# Generated by Django 4.2.2 on 2023-12-05 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0114_membershipsubscription_canceled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='type',
            field=models.CharField(choices=[('subscription', 'Subscription'), ('donation', 'Donation'), ('merchandise', 'Merchandise'), ('fees', 'Fees'), ('adverts', 'Adverts'), ('one off', 'One Off')], default='subscription', max_length=25, null=True, verbose_name='Payment Type'),
        ),
    ]
