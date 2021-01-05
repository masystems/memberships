# Generated by Django 3.1.2 on 2021-01-05 22:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0052_membershipsubscription_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershippackage',
            name='business_type',
            field=models.CharField(choices=[('individual', 'Individual'), ('company', 'Company '), ('non_profit', 'Non Profit ')], default='individual', help_text='Select your business type', max_length=19),
        ),
    ]
