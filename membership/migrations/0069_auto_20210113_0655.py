# Generated by Django 3.1.2 on 2021-01-13 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0068_auto_20210112_1943'),
    ]

    operations = [
        migrations.AddField(
            model_name='equine',
            name='area_code',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='do_not_mail_reason',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='home_telephone',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='equine',
            name='second_name',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AddField(
            model_name='member',
            name='company',
            field=models.CharField(blank=True, help_text='Only to be used if is a company account', max_length=255),
        ),
        migrations.AddField(
            model_name='member',
            name='country',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
