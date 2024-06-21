# Generated by Django 4.2.2 on 2024-06-21 22:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0116_alter_payment_comments'),
    ]

    operations = [
        migrations.AddField(
            model_name='membershippackage',
            name='payment_increments',
            field=models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly')], default='monthly', help_text='In what increments your payments are made', max_length=12, null=True),
        ),
    ]
