# Generated by Django 3.1.2 on 2021-01-10 15:44

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0056_membershipsubscription_payment_method'),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.CharField(blank=True, max_length=255)),
                ('comments', models.TextField(blank=True)),
                ('created', models.DateField(default=datetime.datetime.now)),
                ('subscription', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='membership.member', verbose_name='Subscription Payment')),
            ],
        ),
    ]
