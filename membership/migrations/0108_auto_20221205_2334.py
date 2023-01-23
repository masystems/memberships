# Generated by Django 3.1.2 on 2022-12-05 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0107_membershipsubscription_stripe_payment_token'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='membershippackage',
            name='cloud_lines_account',
        ),
        migrations.AddField(
            model_name='membershippackage',
            name='cloud_lines_domain',
            field=models.CharField(blank=True, default='cloud-lines.com', help_text='Link your membership account to your cloud-lines account', max_length=100),
        ),
        migrations.AddField(
            model_name='membershippackage',
            name='cloud_lines_token',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]