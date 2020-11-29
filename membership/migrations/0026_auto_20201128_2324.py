# Generated by Django 3.1.2 on 2020-11-28 23:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0025_auto_20201128_2315'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='standing_order_amount',
        ),
        migrations.AddField(
            model_name='member',
            name='billing_period',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly ')], default='monthly', help_text='Payment frequency', max_length=19, null=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='payment_type',
            field=models.CharField(choices=[('cash', 'Cash'), ('cheque', 'Cheque '), ('standing_order', 'Standing Order'), ('caf_standing_order', 'CAF standing Order'), ('petty_cash', 'Petty Cash'), ('card_payment', 'Card Payment'), ('bacs', 'BACS'), ('caf_voucher', 'Caf Voucher'), ('postal_cheque ', 'Postal Cheque'), ('paypal', 'Paypal')], default='card_payment', help_text='Payment type used by member', max_length=19, null=True),
        ),
    ]
