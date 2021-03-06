# Generated by Django 3.1.2 on 2020-11-28 23:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0024_auto_20201128_2305'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershippackage',
            name='membership_price_per_month_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='membershippackage',
            name='membership_price_per_year_id',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='membershippackage',
            name='membership_price_per_month',
            field=models.DecimalField(decimal_places=2, help_text='Price in £ per month', max_digits=5),
        ),
        migrations.AlterField(
            model_name='membershippackage',
            name='membership_price_per_year',
            field=models.DecimalField(decimal_places=2, help_text='Price in £ per year', max_digits=5),
        ),
    ]
