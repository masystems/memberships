# Generated by Django 3.1.2 on 2021-01-15 12:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0081_auto_20210115_0558'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membershipsubscription',
            name='payment_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='spayment_method', to='membership.paymentmethod', verbose_name='Payment Method'),
        ),
    ]
