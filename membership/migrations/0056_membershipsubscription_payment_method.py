# Generated by Django 3.1.2 on 2021-01-09 23:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0055_remove_paymentmethod_payment_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershipsubscription',
            name='payment_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payment_method', to='membership.paymentmethod', verbose_name='Payment Method'),
        ),
    ]